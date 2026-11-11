"""Offline HTTP-boundary checks; every provider operation uses MockTransport."""
from __future__ import annotations

import asyncio
from decimal import Decimal
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
DEVON = Path(r"C:\Users\dreac\Desktop\kdt\devon")
for folder in (LAB, DEVON / "backend", DEVON / "ai" / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import httpx
from cost_accounting import BudgetRejected, CostBudget


MODEL = "offline-exact-model"
ENDPOINT = "https://offline.invalid/tenant/v1/responses"
LIMITS = {MODEL: {"max_input_bytes": 10000, "max_output_tokens": 100,
                  "max_response_bytes": 10000}}
PRICING = {"models": {MODEL: {
    "input_usd_per_million": Decimal("1"), "output_usd_per_million": Decimal("2"),
    "cached_input_usd_per_million": Decimal("0.25"),
    "reasoning_output_usd_per_million": Decimal("3"),
    "source_url": "https://offline.invalid/prices", "checked_at": "2026-11-10",
    "price_version": "offline-fixture"}}}


def request_body(**changes):
    return {"model": MODEL, "instructions": "fixture-private-instructions",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": "fixture-private-input"}]}],
            "text": {"format": {"type": "json_schema", "name": "test", "schema": {"type": "object"}, "strict": True}},
            "max_output_tokens": 100, "store": False, **changes}


def envelope(**changes):
    return {"model": MODEL, "id": "resp_fixture", "status": "completed",
            "usage": {"input_tokens": 100, "output_tokens": 20,
                      "input_tokens_details": {"cached_tokens": 40},
                      "output_tokens_details": {"reasoning_tokens": 5}},
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": '{"ok":true}'}]}], **changes}


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            if isinstance(chunk, BaseException):
                raise chunk
            yield chunk

    async def aclose(self):
        self.closed = True


class GuardedTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # A mistaken test/client path must fail instead of opening a connection.
        self.network_block = patch.object(httpx.AsyncHTTPTransport, "handle_async_request",
                                          side_effect=AssertionError("real_network_forbidden"))
        self.network_block.start()
        self.addCleanup(self.network_block.stop)

    def module(self):
        self.assertTrue((LAB / "adapters" / "guarded_transport.py").is_file(),
                        "HTTP-boundary budget guard has not been implemented")
        return importlib.import_module("adapters.guarded_transport")

    def guard(self, handler=None, *, budget=None, pricing=None, limits=None, audit=None, **kwargs):
        return self.module().GuardedTransport(
            httpx.MockTransport(handler or (lambda request: httpx.Response(200, json=envelope()))),
            budget=budget or CostBudget(Decimal("1"), 10, approved=True),
            pricing=pricing or PRICING, allowed_models={MODEL}, allowed_endpoint=ENDPOINT,
            allowed_limits=limits or LIMITS, audit_callback=audit, **kwargs)

    async def send(self, guard, body=None, url=ENDPOINT, **kwargs):
        async with httpx.AsyncClient(transport=guard) as client:
            return await client.post(url, json=body or request_body(), **kwargs)

    async def test_reserves_before_send_and_settles_cached_reasoning_without_double_counting(self):
        budget = CostBudget(Decimal("1"), 2, approved=True)
        audit = []
        def provider(request):
            snapshot = budget.to_dict()
            self.assertEqual(snapshot["attempts_started"], 1)
            self.assertEqual(snapshot["in_flight_attempts"], 1)
            self.assertEqual(audit[0]["event"], "reserved")
            return httpx.Response(200, json=envelope())
        await self.send(self.guard(provider, budget=budget, audit=audit.append))
        # (60*1 + 40*.25 + 15*2 + 5*3) / 1M = .000115.
        self.assertEqual(budget.to_dict()["spent_usd"], "0.000115")
        self.assertEqual(budget.to_dict()["in_flight_attempts"], 0)
        self.assertEqual([row["event"] for row in audit], ["reserved", "settled"])
        self.assertEqual(audit[-1]["cached_input_tokens"], 40)
        self.assertEqual(audit[-1]["reasoning_output_tokens"], 5)
        self.assertEqual(audit[-1]["response_id"], "resp_fixture")

    async def test_distinct_special_rates_reserve_the_higher_prices(self):
        budget = CostBudget(Decimal("1"), 1, approved=True)
        audit = []
        guard = self.guard(budget=budget, audit=audit.append)
        body = json.dumps(request_body(), separators=(",", ":")).encode()
        async with httpx.AsyncClient(transport=guard) as client:
            await client.post(ENDPOINT, content=body)
        expected = Decimal(len(body) + 300) / Decimal(1000000)
        self.assertEqual(Decimal(audit[0]["reserved_usd"]), expected)

    async def test_exact_attempt_cap_blocks_a_second_http_send(self):
        budget = CostBudget(Decimal("1"), 1, approved=True)
        sends = []
        guard = self.guard(lambda request: sends.append(1) or httpx.Response(200, json=envelope()), budget=budget)
        async with httpx.AsyncClient(transport=guard) as client:
            await client.post(ENDPOINT, json=request_body())
            with self.assertRaisesRegex(BudgetRejected, "attempt_cap_reached"):
                await client.post(ENDPOINT, json=request_body())
        self.assertEqual(sends, [1])

    async def test_insufficient_money_blocks_before_delegate(self):
        budget = CostBudget(Decimal("0.000001"), 5, approved=True)
        sends = []
        with self.assertRaisesRegex(BudgetRejected, "monetary_cap_insufficient"):
            await self.send(self.guard(lambda request: sends.append(1), budget=budget))
        self.assertEqual(sends, [])
        self.assertEqual(budget.to_dict()["attempts_started"], 0)

    async def test_invalid_outgoing_request_does_not_consume_or_send(self):
        for body, url, method in ((request_body(model="unapproved"), ENDPOINT, "POST"),
                                  (request_body(), ENDPOINT + "/other", "POST"),
                                  (request_body(), ENDPOINT, "GET"),
                                  (request_body(max_output_tokens=101), ENDPOINT, "POST"),
                                  (request_body(max_output_tokens=True), ENDPOINT, "POST"),
                                  (request_body(tools=[{"type": "web_search"}]), ENDPOINT, "POST")):
            with self.subTest(body=body, url=url, method=method):
                budget = CostBudget(Decimal("1"), 2, approved=True)
                sends = []
                async with httpx.AsyncClient(transport=self.guard(lambda request: sends.append(1), budget=budget)) as client:
                    with self.assertRaises(BudgetRejected):
                        await client.request(method, url, json=body)
                self.assertEqual(sends, [])
                self.assertEqual(budget.to_dict()["attempts_started"], 0)

    async def test_missing_price_or_limits_rejects_before_any_http(self):
        for changes in ({"pricing": {"models": {}}}, {"limits": {"other": LIMITS[MODEL]}}):
            with self.subTest(changes=changes):
                with self.assertRaises(BudgetRejected):
                    self.guard(**changes)

    async def test_missing_usage_malformed_response_or_changed_model_halts_all_later_sends(self):
        for body in (envelope(usage=None), envelope(model="unexpected-model"), b"not-json",
                     envelope(usage={"input_tokens": 100, "output_tokens": 20}),
                     envelope(usage={"input_tokens": True, "output_tokens": 20})):
            with self.subTest(body=body):
                budget = CostBudget(Decimal("1"), 5, approved=True)
                audit, sends = [], []
                def provider(request):
                    sends.append(1)
                    return httpx.Response(200, content=body) if isinstance(body, bytes) else httpx.Response(200, json=body)
                guard = self.guard(provider, budget=budget, audit=audit.append)
                async with httpx.AsyncClient(transport=guard) as client:
                    for _ in range(2):
                        with self.assertRaises(BudgetRejected):
                            await client.post(ENDPOINT, json=request_body())
                self.assertEqual(sends, [1])
                self.assertEqual(budget.to_dict()["unknown_attempts"], 1)
                self.assertEqual(budget.to_dict()["in_flight_attempts"], 0)
                settled = [row for row in audit if row["event"] == "settled"]
                self.assertEqual(len(settled), 1)
                self.assertIsNone(settled[0]["cost_usd"])
                self.assertEqual(audit[-1]["event"], "rejected")

    async def test_network_error_and_cancellation_make_billing_unknown(self):
        for error in (httpx.ConnectError("fixture-secret-error"), asyncio.CancelledError()):
            with self.subTest(error=type(error)):
                budget = CostBudget(Decimal("1"), 5, approved=True)
                audit = []
                def provider(request):
                    raise error
                guard = self.guard(provider, budget=budget, audit=audit.append)
                with self.assertRaises((BudgetRejected, asyncio.CancelledError)):
                    await self.send(guard)
                self.assertTrue(budget.to_dict()["halted"])
                self.assertEqual(budget.to_dict()["unknown_attempts"], 1)
                self.assertEqual(audit[-1]["event"], "settled")
                self.assertNotIn("fixture-secret-error", json.dumps(audit))

    async def test_oversized_or_interrupted_response_settles_unknown_and_closes_stream(self):
        for chunks in ([b"x" * 10001], [b"{", httpx.ReadError("fixture-private-error")]):
            with self.subTest(chunks=len(chunks)):
                budget = CostBudget(Decimal("1"), 5, approved=True)
                source = Chunks(chunks)
                guard = self.guard(lambda request: httpx.Response(200, stream=source), budget=budget)
                with self.assertRaises(BudgetRejected):
                    await self.send(guard)
                self.assertTrue(source.closed)
                self.assertEqual(budget.to_dict()["unknown_attempts"], 1)

    async def test_unconsumed_response_close_halts_future_sends(self):
        budget = CostBudget(Decimal("1"), 5, approved=True)
        source = Chunks([json.dumps(envelope()).encode()])
        guard = self.guard(lambda request: httpx.Response(200, stream=source), budget=budget)
        async with httpx.AsyncClient(transport=guard) as client:
            response = await client.send(client.build_request("POST", ENDPOINT, json=request_body()), stream=True)
            await response.aclose()
            with self.assertRaises(BudgetRejected):
                await client.post(ENDPOINT, json=request_body())
        self.assertTrue(source.closed)
        self.assertEqual(budget.to_dict()["unknown_attempts"], 1)

    async def test_http_error_with_usage_charges_and_error_without_usage_halts(self):
        for usage_present in (True, False):
            with self.subTest(usage_present=usage_present):
                budget = CostBudget(Decimal("1"), 5, approved=True)
                body = envelope(status="failed", error={"code": "fixture-error"}) if usage_present else {"error": {"code": "fixture-error"}}
                guard = self.guard(lambda request: httpx.Response(503, json=body), budget=budget)
                async with httpx.AsyncClient(transport=guard) as client:
                    if usage_present:
                        async with client.stream("POST", ENDPOINT, json=request_body()) as response:
                            self.assertEqual(response.status_code, 503)
                        self.assertEqual(budget.to_dict()["spent_usd"], "0.000115")
                    else:
                        with self.assertRaises(BudgetRejected):
                            await client.post(ENDPOINT, json=request_body())
                        self.assertEqual(budget.to_dict()["unknown_attempts"], 1)

    async def test_complete_sse_usage_is_charged_and_truncation_is_unknown(self):
        for complete in (True, False):
            with self.subTest(complete=complete):
                budget = CostBudget(Decimal("1"), 5, approved=True)
                raw = 'data: ' + json.dumps({"type": "response.completed", "response": envelope()}) + ('\n\n' if complete else '')
                guard = self.guard(lambda request: httpx.Response(200, content=raw, headers={"content-type": "text/event-stream"}), budget=budget)
                if complete:
                    await self.send(guard, request_body(stream=True))
                    self.assertEqual(budget.to_dict()["spent_usd"], "0.000115")
                else:
                    with self.assertRaises(BudgetRejected):
                        await self.send(guard, request_body(stream=True))
                    self.assertEqual(budget.to_dict()["unknown_attempts"], 1)

    async def test_audit_contains_only_allowlisted_metadata_and_reservation_is_durable_before_http(self):
        audit = []
        guard = self.guard(audit=audit.append)
        await self.send(guard, headers={"Authorization": "Bearer fixture-secret-key"})
        rendered = json.dumps(audit)
        for secret in ("fixture-secret-key", "fixture-private-input", "fixture-private-instructions", '{"ok":true}'):
            self.assertNotIn(secret, rendered)
        self.assertEqual(audit[-1]["model"], MODEL)

    async def test_audit_write_failure_prevents_send_and_halts(self):
        sends = []
        def broken_audit(row):
            raise OSError("fixture-private-filesystem-error")
        budget = CostBudget(Decimal("1"), 5, approved=True)
        with self.assertRaisesRegex(BudgetRejected, "audit_persistence_failed"):
            await self.send(self.guard(lambda request: sends.append(1), budget=budget, audit=broken_audit))
        self.assertEqual(sends, [])
        self.assertTrue(budget.to_dict()["halted"])

    async def test_rejected_outgoing_request_records_terminal_state_without_starting_attempt(self):
        audit = []
        guard = self.guard(audit=audit.append)
        with self.assertRaisesRegex(BudgetRejected, "model_not_approved"):
            await self.send(guard, request_body(model="not-approved"))
        self.assertTrue(guard.snapshot()["halted"])
        self.assertEqual(guard.snapshot()["budget"]["attempts_started"], 0)
        self.assertEqual(audit[-1]["event"], "rejected")
        self.assertEqual(audit[-1]["error_code"], "model_not_approved")

    async def test_client_shutdown_marks_a_dangling_response_unknown_and_closes_it(self):
        budget = CostBudget(Decimal("1"), 5, approved=True)
        source = Chunks([json.dumps(envelope()).encode()])
        guard = self.guard(lambda request: httpx.Response(200, stream=source), budget=budget)
        async with httpx.AsyncClient(transport=guard) as client:
            await client.send(client.build_request("POST", ENDPOINT, json=request_body()), stream=True)
        self.assertEqual(budget.to_dict()["unknown_attempts"], 1)
        self.assertEqual(budget.to_dict()["in_flight_attempts"], 0)
        self.assertTrue(source.closed)

    async def test_cancelled_response_consumption_persists_unknown_usage_and_closes_source(self):
        budget = CostBudget(Decimal("1"), 5, approved=True)
        audit = []
        source = Chunks([b"{", asyncio.CancelledError()])
        guard = self.guard(lambda request: httpx.Response(200, stream=source), budget=budget, audit=audit.append)
        with self.assertRaises(asyncio.CancelledError):
            await self.send(guard)
        self.assertEqual(budget.to_dict()["unknown_attempts"], 1)
        self.assertEqual(audit[-1]["error_code"], "attempt_cancelled")
        self.assertTrue(source.closed)

    async def test_actual_cost_over_estimate_is_recorded_and_stops_even_with_usd_remaining(self):
        budget = CostBudget(Decimal("1"), 5, approved=True)
        result = envelope(usage={"input_tokens": 100000, "output_tokens": 0,
                                 "input_tokens_details": {"cached_tokens": 0},
                                 "output_tokens_details": {"reasoning_tokens": 0}})
        guard = self.guard(lambda request: httpx.Response(200, json=result), budget=budget)
        with self.assertRaisesRegex(BudgetRejected, "actual_cost_reservation_exceeded"):
            await self.send(guard)
        self.assertEqual(budget.to_dict()["spent_usd"], "0.1")
        self.assertEqual(budget.to_dict()["unknown_attempts"], 0)
        self.assertTrue(guard.snapshot()["halted"])
        self.assertEqual(guard.snapshot()["attempts"][-1]["cost_usd"], "0.1")

    async def test_settlement_audit_failure_still_closes_response_and_stops_next_http(self):
        source = Chunks([json.dumps(envelope()).encode()])
        audit = []
        def failing_settle(row):
            audit.append(row)
            if row["event"] == "settled":
                raise OSError("private-local-path")
        guard = self.guard(lambda request: httpx.Response(200, stream=source), audit=failing_settle)
        with self.assertRaisesRegex(BudgetRejected, "audit_persistence_failed"):
            await self.send(guard)
        self.assertTrue(source.closed)
        self.assertTrue(guard.snapshot()["halted"])

    async def test_input_byte_cap_duplicate_json_and_media_cannot_bypass_guard(self):
        invalid = [json.dumps(request_body(instructions="x" * 10001)).encode(),
                   b'{"model":"a","model":"b"}',
                   json.dumps(request_body(input=[{"role": "user", "content": [
                       {"type": "input_image", "image_url": "https://private.invalid/image"}]}])).encode()]
        for body in invalid:
            with self.subTest(size=len(body)):
                guard = self.guard()
                async with httpx.AsyncClient(transport=guard) as client:
                    with self.assertRaises(BudgetRejected):
                        await client.post(ENDPOINT, content=body)
                self.assertEqual(guard.snapshot()["budget"]["attempts_started"], 0)

    async def test_missing_optional_special_price_does_not_assume_nonzero_usage_is_free(self):
        pricing = {"models": {MODEL: {**PRICING["models"][MODEL],
                                     "cached_input_usd_per_million": None}}}
        guard = self.guard(pricing=pricing)
        with self.assertRaises(BudgetRejected):
            await self.send(guard)
        self.assertEqual(guard.snapshot()["budget"]["unknown_attempts"], 1)

    async def test_guard_requests_identity_encoding_for_bounded_usage_capture(self):
        def provider(request):
            self.assertEqual(request.headers["Accept-Encoding"], "identity")
            return httpx.Response(200, json=envelope())
        await self.send(self.guard(provider))

    async def test_compressed_response_is_rejected_without_decoding_unbounded_bytes(self):
        source = Chunks([b"compressed-or-invalid-provider-body"])
        guard = self.guard(lambda request: httpx.Response(200, stream=source, headers={"content-encoding": "gzip"}))
        with self.assertRaisesRegex(BudgetRejected, "response_encoding_not_supported"):
            await self.send(guard)
        self.assertTrue(source.closed)
        self.assertEqual(guard.snapshot()["budget"]["unknown_attempts"], 1)

    async def test_json_http_error_usage_is_charged_when_original_request_enabled_sse(self):
        budget = CostBudget(Decimal("1"), 5, approved=True)
        guard = self.guard(lambda request: httpx.Response(503, json=envelope(status="failed")), budget=budget)
        response = await self.send(guard, request_body(stream=True))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(budget.to_dict()["spent_usd"], "0.000115")

    async def test_original_call_model_parse_retry_is_charged_on_every_http_attempt(self):
        from app.integrations.llm.client import call_model
        from devon_ai import contracts as c
        from pydantic import SecretStr
        budget = CostBudget(Decimal("1"), 5, approved=True)
        audit, sends = [], []
        def provider(request):
            sends.append(1)
            result = envelope()
            if len(sends) == 1:
                result["output"][0]["content"][0]["text"] = "not-json"
            return httpx.Response(200, json=result)
        request = c.ModelRequest(
            prompt=c.PromptSpec(task_name="fixture", version="fixture", model=MODEL, template="fixture"),
            payload={"fixture": True}, schema_name="fixture", schema_version="fixture",
            output_schema={"type": "object"}, limits=c.CallLimits(max_input_bytes=10000,
                max_output_tokens=100, max_response_bytes=10000, timeout_seconds=10), max_attempts=2)
        async with httpx.AsyncClient(transport=self.guard(provider, budget=budget, audit=audit.append)) as client:
            result = await call_model(request, lambda value: value, api_key=SecretStr("fixture-key"),
                                      base_url=ENDPOINT.removesuffix("/responses"), http_client=client)
        self.assertIsNone(result.failure)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(sends, [1, 1])
        self.assertEqual(budget.to_dict()["spent_usd"], "0.00023")
        self.assertEqual([row["event"] for row in audit], ["reserved", "settled", "reserved", "settled"])

    async def test_original_schema_retry_is_charged_and_exact_usd_cap_prevents_second_send(self):
        from app.integrations.llm.client import call_model
        from devon_ai import contracts as c
        from pydantic import SecretStr
        for amount, expected_sends in (("1", 2), ("0.0007", 1)):
            with self.subTest(amount=amount):
                budget = CostBudget(Decimal(amount), 5, approved=True)
                sends = []
                guard = self.guard(lambda request: sends.append(1) or httpx.Response(200, json=envelope()), budget=budget)
                request = c.ModelRequest(
                    prompt=c.PromptSpec(task_name="fixture", version="fixture", model=MODEL, template="fixture"),
                    payload={"fixture": True}, schema_name="fixture", schema_version="fixture",
                    output_schema={"type": "object"}, limits=c.CallLimits(max_input_bytes=10000,
                        max_output_tokens=100, max_response_bytes=10000, timeout_seconds=10), max_attempts=2)
                validations = []
                def validator(value):
                    validations.append(1)
                    if len(validations) == 1:
                        raise c.ContractError("schema", "fixture")
                    return value
                async with httpx.AsyncClient(transport=guard) as client:
                    if amount == "1":
                        result = await call_model(request, validator, api_key=SecretStr("fixture-key"),
                            base_url=ENDPOINT.removesuffix("/responses"), http_client=client)
                        self.assertIsNone(result.failure)
                        self.assertEqual(len(result.attempts), 2)
                    else:
                        with self.assertRaisesRegex(BudgetRejected, "monetary_cap_insufficient"):
                            await call_model(request, validator, api_key=SecretStr("fixture-key"),
                                base_url=ENDPOINT.removesuffix("/responses"), http_client=client)
                self.assertEqual(len(sends), expected_sends)
                self.assertEqual(budget.to_dict()["spent_usd"], "0.00023" if expected_sends == 2 else "0.000115")

    async def test_original_plan_and_review_calls_share_one_http_budget(self):
        from app.integrations.llm.client import call_model
        from devon_ai import contracts as c
        from pydantic import SecretStr
        budget = CostBudget(Decimal("1"), 1, approved=True)
        sends = []
        guard = self.guard(lambda request: sends.append(1) or httpx.Response(200, json=envelope()), budget=budget)
        async with httpx.AsyncClient(transport=guard) as client:
            for task in ("director_plan", "director_review"):
                request = c.ModelRequest(
                    prompt=c.PromptSpec(task_name=task, version="fixture", model=MODEL, template="fixture"),
                    payload={"fixture": True}, schema_name=task, schema_version="fixture",
                    output_schema={"type": "object"}, limits=c.CallLimits(max_input_bytes=10000,
                        max_output_tokens=100, max_response_bytes=10000, timeout_seconds=10), max_attempts=1)
                if task == "director_plan":
                    result = await call_model(request, lambda value: value, api_key=SecretStr("fixture-key"),
                        base_url=ENDPOINT.removesuffix("/responses"), http_client=client)
                    self.assertIsNone(result.failure)
                else:
                    with self.assertRaisesRegex(BudgetRejected, "attempt_cap_reached"):
                        await call_model(request, lambda value: value, api_key=SecretStr("fixture-key"),
                            base_url=ENDPOINT.removesuffix("/responses"), http_client=client)
        self.assertEqual(sends, [1])
        self.assertEqual(budget.to_dict()["attempts_started"], 1)


if __name__ == "__main__":
    unittest.main()
