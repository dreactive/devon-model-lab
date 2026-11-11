"""Per-HTTP-attempt USD guard for the original Responses client.

The caller supplies an already approved policy and a delegate created after
preflight. This module never constructs a network transport or reads secrets.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal, localcontext
import json
import re
from typing import Any

import httpx

from cost_accounting import BudgetRejected, CostBudget, MILLION, _attempt_cost, _lookup, _usd


def _json(raw: bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite_json_number")

    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    stack = [(result, 1)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, (dict, list)):
            if depth > 64:
                raise ValueError("json_depth_exceeded")
            children = item.values() if isinstance(item, dict) else item
            stack.extend((child, depth + 1) for child in children)
    return result


class GuardedTransport(httpx.AsyncBaseTransport):
    """Reserve before every delegate send and settle only complete bounded usage.

    `allowed_endpoint` is the full, approved HTTPS `/responses` URL. Limits are
    positive integer caps indexed by exact model ID. One instance and CostBudget
    must cover service, review, retries and any enabled judge calls together.
    """

    def __init__(self, delegate: httpx.AsyncBaseTransport, *, budget: CostBudget,
                 pricing: dict, allowed_models: set[str], allowed_endpoint: str,
                 allowed_limits: dict[str, dict[str, int]],
                 audit_callback: Callable[[dict], None] | None = None) -> None:
        self._delegate, self.budget = delegate, budget
        self._audit_callback = audit_callback
        self._halt_reason: str | None = None
        self._attempts: list[dict] = []
        self._streams: set[_UsageStream] = set()
        try:
            endpoint = httpx.URL(allowed_endpoint)
            if (endpoint.scheme != "https" or not endpoint.host or endpoint.username
                    or endpoint.password or endpoint.query or endpoint.fragment
                    or not endpoint.path.endswith("/responses")):
                raise ValueError
            if not allowed_models or any(type(model) is not str or not model.strip() for model in allowed_models):
                raise ValueError
            self._models = frozenset(allowed_models)
            self._limits = {}
            self._pricing = {"models": {}}
            for model in self._models:
                record = _lookup(pricing, model)
                if record is None or record["status"] != "collected":
                    raise BudgetRejected("model_price_not_collected")
                caps = allowed_limits.get(model)
                names = ("max_input_bytes", "max_output_tokens", "max_response_bytes")
                if (type(caps) is not dict or any(type(caps.get(name)) is not int
                                                or caps[name] < 1 for name in names)):
                    raise BudgetRejected("approved_limits_missing_or_invalid")
                self._pricing["models"][model] = record
                self._limits[model] = {name: caps[name] for name in names}
            self._endpoint = endpoint
        except BudgetRejected:
            raise
        except (ValueError, TypeError, AttributeError, httpx.InvalidURL):
            raise BudgetRejected("transport_policy_invalid") from None

    def snapshot(self) -> dict:
        budget = self.budget.to_dict()
        budget["transport_integration"] = "http_attempt_guard"
        reason = self._halt_reason or budget["halt_reason"]
        return {"budget": budget, "halted": reason is not None,
                "halt_reason": reason, "attempts": deepcopy(self._attempts),
                "transport_integration": "http_attempt_guard"}

    def _audit(self, row: dict) -> None:
        state = self.snapshot()
        row.update(budget=state["budget"], halted=state["halted"], halt_reason=state["halt_reason"])
        if self._audit_callback is not None:
            try:
                self._audit_callback(deepcopy(row))
            except BaseException:
                self._halt_reason = "audit_persistence_failed"
                raise BudgetRejected("audit_persistence_failed") from None

    def _request(self, request: httpx.Request) -> tuple[str, int, bool, Decimal]:
        state = self.snapshot()
        if state["halted"]:
            raise BudgetRejected(state["halt_reason"])
        if request.method != "POST" or request.url != self._endpoint:
            raise BudgetRejected("endpoint_not_approved")
        if request.headers.get("content-encoding", "identity").lower() != "identity":
            raise BudgetRejected("request_encoding_not_supported")
        try:
            raw = request.content
            if len(raw) > max(caps["max_input_bytes"] for caps in self._limits.values()):
                raise BudgetRejected("approved_input_cap_exceeded")
            body = _json(raw)
            if type(body) is not dict:
                raise ValueError
            model = body.get("model")
            if type(model) is not str or model not in self._models:
                raise BudgetRejected("model_not_approved")
            caps = self._limits[model]
            if len(raw) > caps["max_input_bytes"]:
                raise BudgetRejected("approved_input_cap_exceeded")
            maximum = body.get("max_output_tokens")
            if type(maximum) is not int or not 1 <= maximum <= caps["max_output_tokens"]:
                raise BudgetRejected("approved_output_cap_exceeded")
            allowed_keys = {"model", "instructions", "input", "text", "max_output_tokens", "store", "reasoning", "stream"}
            if set(body) - allowed_keys or type(body.get("instructions")) is not str or body.get("store") is not False:
                raise ValueError
            # Only the original text/schema request shape is priced here. Tools,
            # images, attachments, stored context and background jobs need their
            # own explicit accounting policy and cannot slip through this seam.
            inputs = body.get("input")
            if type(inputs) is not list or not inputs:
                raise ValueError
            for item in inputs:
                if (type(item) is not dict or set(item) != {"role", "content"}
                        or item["role"] != "user" or type(item["content"]) is not list
                        or not item["content"]):
                    raise ValueError
                for content in item["content"]:
                    if (type(content) is not dict or set(content) != {"type", "text"}
                            or content["type"] != "input_text" or type(content["text"]) is not str):
                        raise ValueError
            if type(body.get("text")) is not dict:
                raise ValueError
            stream = body.get("stream", False)
            if type(stream) is not bool:
                raise ValueError
            if "reasoning" in body and (type(body["reasoning"]) is not dict
                    or set(body["reasoning"]) != {"effort"}
                    or body["reasoning"]["effort"] not in ("none", "minimal", "low", "medium", "high", "xhigh")):
                raise ValueError
            rates = self._pricing["models"][model]
            input_rate = max(rates["input_usd_per_million"], rates["cached_input_usd_per_million"] or Decimal(0))
            output_rate = max(rates["output_usd_per_million"], rates["reasoning_output_usd_per_million"] or Decimal(0))
            with localcontext() as context:
                context.prec = max(50, len(str(len(raw))) + len(str(maximum))
                                   + len(str(input_rate)) + len(str(output_rate)) + 20)
                upper = (Decimal(len(raw)) * input_rate + Decimal(maximum) * output_rate) / MILLION
            return model, caps["max_response_bytes"], stream, upper
        except BudgetRejected:
            raise
        except (ValueError, TypeError, UnicodeError, RecursionError, httpx.RequestNotRead):
            raise BudgetRejected("request_shape_not_supported") from None

    def _settle(self, ticket: str, model: str, upper: Decimal, *, raw: bytes | None,
                stream: bool, error_code: str | None = None) -> None:
        record: dict = {"event": "settled", "attempt_id": ticket, "model": model,
                        "reserved_usd": _usd(upper), "cost_usd": None,
                        "response_id": None, "error_code": error_code}
        actual = None
        if raw is not None:
            try:
                if stream:
                    from app.integrations.llm.client import _stream_envelope
                    envelope = _stream_envelope(raw)
                else:
                    envelope = _json(raw)
                if type(envelope) is not dict:
                    raise ValueError
                actual_model = envelope.get("model")
                if actual_model != model or actual_model not in self._models:
                    raise ValueError
                usage = envelope.get("usage")
                if type(usage) is not dict:
                    raise ValueError
                tokens = {"model": actual_model,
                          "input_tokens": usage.get("input_tokens"),
                          "output_tokens": usage.get("output_tokens")}
                for group, key, canonical in (("input_tokens_details", "cached_tokens", "cached_input_tokens"),
                                              ("output_tokens_details", "reasoning_tokens", "reasoning_output_tokens")):
                    details = usage.get(group)
                    if type(details) is dict and key in details:
                        tokens[canonical] = details[key]
                    elif group in usage and details is not None:
                        raise ValueError
                calculated = _attempt_cost(tokens, self._pricing)
                actual = calculated["cost_usd"]
                for key, value in tokens.items():
                    if key != "model" and type(value) is int and value >= 0:
                        record[key] = value
                response_id = envelope.get("id")
                if type(response_id) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", response_id):
                    record["response_id"] = response_id
                if actual is None:
                    record["error_code"] = "usage_or_price_breakdown_unconfirmed"
            except Exception:
                record["error_code"] = "response_usage_unconfirmed"
        self.budget.settle(ticket, actual)
        record["cost_usd"] = _usd(actual)
        if actual is None:
            self._halt_reason = self._halt_reason or record["error_code"] or "actual_cost_unconfirmed"
        elif actual > upper:
            self._halt_reason = "actual_cost_reservation_exceeded"
            record["error_code"] = self._halt_reason
        self._attempts.append(record)
        self._audit(record)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            model, maximum, stream, upper = self._request(request)
        except BudgetRejected as error:
            self._halt_reason = self._halt_reason or str(error)
            self._audit({"event": "rejected", "error_code": str(error)})
            raise
        try:
            ticket = self.budget.reserve(upper)
        except BudgetRejected as error:
            self._halt_reason = str(error)
            self._audit({"event": "rejected", "model": model, "error_code": str(error)})
            raise
        try:
            self._audit({"event": "reserved", "attempt_id": ticket,
                         "model": model, "reserved_usd": _usd(upper)})
        except BudgetRejected:
            # The durable reservation record failed, so the delegate must never
            # start. Treat this reservation conservatively and stop the run.
            self.budget.settle(ticket, None)
            raise
        try:
            # Usage capture bounds apply to uncompressed bytes. Original calls
            # do not need HTTP compression; do not negotiate a compressed body.
            request.headers["Accept-Encoding"] = "identity"
            response = await self._delegate.handle_async_request(request)
        except BaseException as error:
            self._settle(ticket, model, upper, raw=None, stream=stream,
                         error_code="attempt_cancelled" if isinstance(error, asyncio.CancelledError) else "transport_failed")
            if isinstance(error, asyncio.CancelledError):
                raise
            raise BudgetRejected("actual_cost_unconfirmed") from None
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        accounting_stream = stream if response.is_success else content_type == "text/event-stream"
        tap = _UsageStream(response.stream, self, ticket, model, upper, maximum, accounting_stream)
        self._streams.add(tap)
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            try:
                tap._finish(None, "response_encoding_not_supported")
            finally:
                await tap.aclose()
            raise BudgetRejected("response_encoding_not_supported")
        wrapped = httpx.Response(response.status_code, headers=response.headers, stream=tap,
                                 extensions=response.extensions, request=request)
        if not response.is_success:
            # The original client does not consume most HTTP error bodies.
            # Read through the same bounded tap to account explicit usage and
            # refuse automatic "free" retries when that usage is unavailable.
            try:
                raw = await wrapped.aread()
            finally:
                await wrapped.aclose()
            return httpx.Response(response.status_code, headers=response.headers, content=raw,
                                  extensions=response.extensions, request=request)
        return wrapped

    async def aclose(self) -> None:
        failure: BaseException | None = None
        for stream in tuple(self._streams):
            try:
                await stream.aclose()
            except BaseException as error:
                failure = failure or error
        try:
            await self._delegate.aclose()
        except BaseException:
            self._halt_reason = "transport_close_failed"
            self._audit({"event": "rejected", "error_code": "transport_close_failed"})
            raise BudgetRejected("transport_close_failed") from None
        if failure is not None:
            raise failure


class _UsageStream(httpx.AsyncByteStream):
    def __init__(self, source: httpx.AsyncByteStream, guard: GuardedTransport,
                 ticket: str, model: str, upper: Decimal, maximum: int, stream: bool) -> None:
        self._source, self._guard = source, guard
        self._ticket, self._model, self._upper = ticket, model, upper
        self._maximum, self._stream = maximum, stream
        self._finished = False
        self._closed = False

    def _finish(self, raw: bytes | None, error_code: str | None = None) -> None:
        if not self._finished:
            self._finished = True
            self._guard._settle(self._ticket, self._model, self._upper,
                                raw=raw, stream=self._stream, error_code=error_code)

    async def __aiter__(self):
        buffer = bytearray()
        try:
            async for chunk in self._source:
                if len(buffer) + len(chunk) > self._maximum:
                    self._finish(None, "response_byte_cap_exceeded")
                    raise BudgetRejected("response_byte_cap_exceeded")
                buffer.extend(chunk)
                yield chunk
            self._finish(bytes(buffer))
            if self._guard.snapshot()["halted"]:
                raise BudgetRejected(self._guard.snapshot()["halt_reason"])
        except BaseException as error:
            self._finish(None, "attempt_cancelled" if isinstance(error, asyncio.CancelledError) else "response_interrupted")
            try:
                await self.aclose()
            finally:
                if isinstance(error, (asyncio.CancelledError, GeneratorExit, BudgetRejected)):
                    raise
                raise BudgetRejected("actual_cost_unconfirmed") from None

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._finish(None, "response_closed_before_usage")
        finally:
            try:
                await self._source.aclose()
            except BaseException:
                # Closing after confirmed usage does not erase that cost.
                self._guard._halt_reason = "response_close_failed"
                self._guard._audit({"event": "rejected", "error_code": "response_close_failed"})
                raise BudgetRejected("response_close_failed") from None
            finally:
                self._guard._streams.discard(self)
