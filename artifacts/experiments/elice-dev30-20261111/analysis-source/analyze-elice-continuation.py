"""Offline lifetime accounting for the one explicitly authorized Elice continuation.

Usage: python -B analyze-elice-continuation.py NEW_RUN_DIRECTORY

Reads immutable parent evidence and fresh results; writes only the three analysis
artifacts in NEW_RUN_DIRECTORY. No environment files, provider clients, or network
modules are used. DEVON is imported lazily only for deterministic B score math.
Draft agreement is diagnostic, never approved accuracy or a pass threshold.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any


MODELS = (
    "gpt-6.1-sol", "gemini-3.8-flash", "gemini-4-argon",
    "claude-haiku-5-5", "claude-sonnet-5-5", "gpt-6-luna",
)
FAILURES = {"failed", "rejected", "interrupted", "budget_stopped"}
HALTS = FAILURES | {"cancelled", "aborted"}
OUTPUT_NAMES = ("analysis.json", "case-accounting.json", "report.md")
MAX_RAW_TRACE_BYTES = 2 * 1024 * 1024
MAX_RAW_TRACE_FILES_PER_JOB = 512
ZERO = Decimal(0)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def money(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() and result >= 0 else None


def token(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def finite_number(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        return float(value) if Decimal(str(value)).is_finite() else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * quantile
    left = int(position)
    right = min(left + 1, len(values) - 1)
    return round(values[left] + (values[right] - values[left]) * (position - left), 3)


def case_latency(row: dict | None, experiment: str) -> dict:
    if row is None:
        return {"latency_ms": None, "latency_source": "unmeasured_no_result_row",
                "service_latency_ms_original": None, "sdk_latency_missing_attempts": 0}
    original = finite_number(row.get("service_latency_ms"))
    measurements = [finite_number(a.get("latency_ms")) for a in row.get("attempts", [])]
    known = [v for v in measurements if v is not None and v >= 0]
    failed_zero = experiment == "A" and row.get("status") in {"failed", "rejected"} and original == 0
    if failed_zero:
        latency = sum(known) if any(v > 0 for v in known) else None
        source = "sdk_attempt_sum_replacing_failed_service_zero_placeholder" if latency is not None else "failed_service_zero_placeholder_unmeasured"
    elif original is not None and original >= 0:
        latency, source = original, "service_wall_time"
    else:
        latency = sum(known) if known else None
        source = "recorded_sdk_attempt_latency_sum" if known else "unmeasured_no_recorded_latency"
    return {"latency_ms": latency, "latency_source": source,
        "service_latency_ms_original": original,
        "sdk_latency_missing_attempts": len(measurements) - len(known)}


def relative_file(directory: Path, value: str) -> Path:
    """All run-local artifacts must stay within their declared run directory."""
    path = (directory / value).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("run_artifact_path_outside_directory")
    return path


def case_identifier(row: dict[str, Any]) -> str:
    identifier = row.get("case_id") or row.get("case") or ""
    return identifier.rsplit(".v", 1)[0]


def case_key(model: str, corpus: str, case_id: str) -> str:
    return "::".join((model, corpus.replace("\\", "/"), case_id))


def origin_id(directory: Path, attempt_id: Any) -> str:
    return f"{directory.resolve().as_posix()}::{attempt_id}"


def load_origin(directory: Path, role: str) -> dict[str, Any]:
    bundle = read_json(directory / "bundle.json")
    ledger_path = directory / "ledger.json"
    campaign_path = directory / "campaign-result.json"
    return {
        "directory": directory, "role": role, "bundle": bundle,
        "ledger": read_json(ledger_path) if ledger_path.exists() else {"events": []},
        "campaign": read_json(campaign_path) if campaign_path.exists() else {},
    }


def load_origin_chain(directory: Path) -> list[dict[str, Any]]:
    """Read each immutable ancestor once, including multiple explicit recoveries."""
    ordered: list[dict] = []
    visited: set[Path] = set()
    visiting: set[Path] = set()

    def visit(path: Path, fresh: bool = False) -> None:
        path = path.resolve()
        if path in visiting:
            raise ValueError("continuation_parent_cycle")
        if path in visited:
            return
        visiting.add(path)
        origin = load_origin(path, "fresh" if fresh else "parent")
        proof = origin["bundle"].get("continuation") or {}
        ancestors = proof.get("ancestor_directories", proof.get("parent_directories", []))
        if not isinstance(ancestors, list):
            raise ValueError("continuation_ancestor_directories_invalid")
        parents = [*ancestors]
        if proof.get("parent_directory"):
            parents.append(proof["parent_directory"])
        for value in parents:
            if not isinstance(value, str) or not value:
                raise ValueError("continuation_parent_directory_invalid")
            parent = Path(value)
            visit(parent if parent.is_absolute() else path / parent)
        visiting.remove(path)
        visited.add(path)
        ordered.append(origin)

    visit(directory, fresh=True)
    if len(ordered) < 2:
        raise ValueError("continuation_parent_directory_missing")
    return ordered


def collect_transport(origins: list[dict[str, Any]], issues: list[dict]) -> list[dict]:
    """Union physical attempts, never collapsing parent/new local attempt IDs."""
    result = []
    for origin in origins:
        directory = origin["directory"]
        reservations: dict[str, dict] = {}
        settled: dict[str, dict] = {}
        for index, raw in enumerate(origin["ledger"].get("events", [])):
            if raw.get("event") not in {"reserved", "settled"}:
                continue
            local = raw.get("attempt_id") or raw.get("local_attempt_id")
            if not local:
                local = f"missing-id-event-{index}"
                issues.append({"code": "transport_attempt_id_missing", "origin": str(directory), "index": index})
            identifier = origin_id(directory, local)
            target = reservations if raw["event"] == "reserved" else settled
            if identifier in target:
                identical = target[identifier] == raw
                issues.append({"code": "duplicate_transport_event", "attempt_id": identifier,
                               "identical": identical, "event": raw["event"]})
                if not identical:
                    target[identifier] = {**target[identifier], "_conflicting_duplicate": True}
                continue
            target[identifier] = dict(raw)
        for identifier in dict.fromkeys([*reservations, *settled]):
            reservation = reservations.get(identifier, {})
            event = settled.get(identifier)
            record = {**reservation, **(event or {}), "origin": str(directory),
                      "origin_role": origin["role"], "physical_attempt_id": identifier,
                      "settled": event is not None, "linked_case_key": None,
                      "linked_sdk_attempt_id": None}
            if event is None:
                record.update(cost_usd=None, cost_lower_usd=None, cost_upper_usd=None,
                              cost_status="unconfirmed", error_code="reservation_without_settlement")
                issues.append({"code": "reservation_without_settlement", "attempt_id": identifier})
            if record.get("_conflicting_duplicate"):
                record.update(cost_usd=None, cost_lower_usd=None, cost_upper_usd=None,
                              cost_status="unconfirmed")
            result.append(record)
    return result


def raw_cache_counter_observation(usage: dict, canonical: dict) -> dict:
    """Preserve the available raw alias without changing live billing values."""
    conflicts = []

    def consistent(fields: list[tuple[str, object]]) -> int | None:
        available = []
        for name, value in fields:
            if value is None:
                continue
            checked = token(value)
            if checked is None:
                conflicts.append(name + ":invalid_counter")
            else:
                available.append(checked)
        if len(set(available)) > 1:
            conflicts.append(fields[0][0] + ":alias_conflict")
        return available[0] if available and len(set(available)) == 1 else None

    inputs = consistent([("raw.input_tokens", usage.get("input_tokens")),
                         ("raw.prompt_tokens", usage.get("prompt_tokens")),
                         ("canonical.input_tokens", canonical.get("input_tokens"))])
    outputs = consistent([("raw.output_tokens", usage.get("output_tokens")),
                          ("raw.completion_tokens", usage.get("completion_tokens")),
                          ("canonical.output_tokens", canonical.get("output_tokens"))])
    writes = [("raw.cache_write_tokens", usage.get("cache_write_tokens")),
              ("raw.cache_write_input_tokens", usage.get("cache_write_input_tokens")),
              ("raw.cache_creation_input_tokens", usage.get("cache_creation_input_tokens")),
              ("canonical.cache_write_input_tokens", canonical.get("cache_write_input_tokens"))]
    reads = [("raw.cached_prompt_tokens", usage.get("cached_prompt_tokens")),
             ("canonical.cached_input_tokens", canonical.get("cached_input_tokens"))]
    for field in ("input_tokens_details", "prompt_tokens_details"):
        detail = usage.get(field)
        if isinstance(detail, dict):
            writes.extend([(f"raw.{field}.cache_write_tokens", detail.get("cache_write_tokens")),
                           (f"raw.{field}.cache_write_input_tokens", detail.get("cache_write_input_tokens"))])
            reads.append((f"raw.{field}.cached_tokens", detail.get("cached_tokens")))
    write = consistent(writes)
    read = consistent(reads)
    if usage.get("total_tokens") is not None:
        total = token(usage["total_tokens"])
        if total is None or inputs is None or outputs is None or total != inputs + outputs:
            conflicts.append("raw.total_tokens:total_conflict")
    if write is not None and (inputs is None or write > inputs):
        conflicts.append("raw.cache_write_tokens:exceeds_input")
    if write is not None and read is not None and inputs is not None and write + read > inputs:
        conflicts.append("raw.cache_write_tokens:read_write_subsets_exceed_input")
    alias = token(usage.get("cache_write_tokens"))
    return {"top_level_alias_present": "cache_write_tokens" in usage,
        "top_level_cache_write_tokens_observed": alias,
        "consistent_cache_write_tokens_observed": write,
        "raw_input_tokens_observed": inputs, "raw_output_tokens_observed": outputs,
        "provider_input_output_totals_present": (
            any(token(usage.get(k)) is not None for k in ("input_tokens", "prompt_tokens"))
            and any(token(usage.get(k)) is not None for k in ("output_tokens", "completion_tokens"))),
        "cached_input_tokens_observed": read, "counter_conflicts": conflicts,
        "write_counter_subset_checked": write is not None and inputs is not None and not conflicts,
        "live_canonical_cache_write_input_tokens": token(canonical.get("cache_write_input_tokens")),
        "available_nonzero_alias_omitted_by_live_normalizer": alias is not None and alias > 0 and canonical.get("cache_write_input_tokens") is None,
        "validated_against_result_sdk_and_transport": False,
        "used_to_change_original_cost_or_guard_debit": False}


def validate_raw_cache_counter(trace: dict, attempt: dict) -> None:
    observed = trace["raw_cache_write_observation"]
    inputs, outputs = token(attempt.get("input_tokens")), token(attempt.get("output_tokens"))
    observed["validated_against_result_sdk_and_transport"] = bool(
        attempt.get("sdk_attempt_id") and observed["write_counter_subset_checked"]
        and observed["provider_input_output_totals_present"]
        and inputs is not None and outputs is not None
        and observed["raw_input_tokens_observed"] == inputs == attempt.get("transport_input_tokens")
        and observed["raw_output_tokens_observed"] == outputs == attempt.get("transport_output_tokens")
        and not attempt.get("token_mismatch_fields"))


def enrich_attempt_with_raw_trace(attempt: dict, trace: dict) -> None:
    attempt["raw_trace"] = trace
    validate_raw_cache_counter(trace, attempt)
    if attempt["technical_failure_cause"] == "request_cancelled":
        return
    cause = trace["technical_cause"]
    if cause not in {"provider_reported_completion", "not_classified"}:
        attempt["technical_failure_cause"] = cause
    elif attempt["explicit_attempt_error"]:
        stage = attempt.get("error_stage")
        provider_stopped = "stop" in trace["finish_reasons"]
        attempt["technical_failure_cause"] = (
            "schema_validation_failed_after_provider_stop" if provider_stopped and stage == "schema"
            else "contract_validation_failed_after_provider_stop" if provider_stopped and stage in {"semantic", "contract", "validation", "post_validation"}
            else "service_validation_or_provider_failure")


def trace_summary(raw: dict, path: Path, content: bytes, event: dict) -> dict:
    """Return bounded diagnostic metadata, never provider output/error text."""
    billing = raw.get("_elice_billing")
    billing = billing if isinstance(billing, dict) else {}
    canonical_usage = billing.get("usage")
    canonical_usage = canonical_usage if isinstance(canonical_usage, dict) else {}
    usage = raw.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    finish_reasons = []
    visible_chars = None
    choices = raw.get("choices")
    allowed_finishes = {"stop", "length", "tool_calls", "function_call", "content_filter"}
    if isinstance(choices, list):
        visible_chars = 0
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            reason = choice.get("finish_reason")
            if reason is not None:
                finish_reasons.append(reason if reason in allowed_finishes else "other")
            message = choice.get("message")
            body = message.get("content") if isinstance(message, dict) else None
            if isinstance(body, str):
                visible_chars += len(body)
            elif isinstance(body, list):
                visible_chars += sum(len(part["text"]) for part in body
                    if isinstance(part, dict) and isinstance(part.get("text"), str))
    elif isinstance(raw.get("output"), list):
        visible_chars = 0
        for item in raw["output"]:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"} and isinstance(part.get("text"), str):
                    visible_chars += len(part["text"])
    allowed_statuses = {"completed", "incomplete", "failed", "cancelled", "queued", "in_progress"}
    status = raw.get("status")
    status = status if isinstance(status, str) and status in allowed_statuses else None
    incomplete = raw.get("incomplete_details")
    incomplete_reason = incomplete.get("reason") if isinstance(incomplete, dict) else None
    incomplete_reason = incomplete_reason if incomplete_reason in {"max_output_tokens", "content_filter"} else "other" if incomplete_reason else None
    truncated = "length" in finish_reasons or incomplete_reason == "max_output_tokens"
    reasoning = token(canonical_usage.get("reasoning_output_tokens"))
    if reasoning is None:
        for name in ("completion_tokens_details", "output_tokens_details"):
            details = usage.get(name)
            if isinstance(details, dict) and token(details.get("reasoning_tokens")) is not None:
                reasoning = details["reasoning_tokens"]
                break
    output = token(canonical_usage.get("output_tokens"))
    if output is None:
        output = token(usage.get("output_tokens", usage.get("completion_tokens")))
    non_reasoning = output - reasoning if output is not None and reasoning is not None and reasoning <= output else None
    wire = raw.get("_elice_wire")
    protocol = wire.get("protocol") if isinstance(wire, dict) else None
    if protocol not in {"chat_completions", "responses"}:
        protocol = "chat_completions" if isinstance(choices, list) else "responses" if isinstance(raw.get("output"), list) else None
    error = raw.get("error")
    error = error if isinstance(error, dict) else {}
    # Error body is used only to recognize explicit compatibility failures. It
    # stays in the redacted raw artifact and is never copied to a report.
    message = str(error.get("message", ""))[:8192].casefold()
    parameter = str(error.get("param", ""))[:128].casefold()
    explicit_rejection = any(word in message for word in ("unsupported", "not support", "doesn't support", "not available", "not implemented", "unknown parameter", "unrecognized", "not allowed", "not permitted"))
    schema_mentioned = any(word in message or word in parameter for word in ("response_format", "json_schema", "json schema", "structured output", "strict"))
    http_status = event.get("http_status")
    schema_incompatible = http_status == 400 and schema_mentioned and explicit_rejection
    if schema_incompatible:
        cause = "http_400_strict_schema_parameter_incompatible"
    elif http_status == 400 and schema_mentioned:
        cause = "http_400_schema_request_rejected"
    elif http_status == 404:
        cause = "http_404_endpoint_not_found"
    elif http_status == 400 and explicit_rejection:
        cause = "http_400_protocol_parameter_incompatible"
    elif type(http_status) is int and http_status >= 400:
        cause = "http_request_rejected"
    elif truncated:
        cause = "output_truncated_at_token_limit"
    elif "content_filter" in finish_reasons or incomplete_reason == "content_filter":
        cause = "provider_content_filter"
    elif error:
        cause = "provider_error"
    elif status == "completed" or "stop" in finish_reasons:
        cause = "provider_reported_completion"
    else:
        cause = "not_classified"
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content), "billing_attempt_id": billing.get("attempt_id"),
        "protocol": protocol, "finish_reasons": finish_reasons,
        "response_status": status, "incomplete_reason": incomplete_reason,
        "truncated": truncated, "reasoning_output_tokens": reasoning,
        "output_tokens_observed": output, "non_reasoning_output_tokens": non_reasoning,
        "visible_output_characters": visible_chars, "technical_cause": cause,
        "explicit_schema_request_rejection": http_status == 400 and schema_mentioned,
        "explicit_strict_schema_incompatibility": schema_incompatible,
        "raw_cache_write_observation": raw_cache_counter_observation(usage, canonical_usage),
        "raw_provider_text_included": False}


def collect_raw_traces(origins: list[dict], events: list[dict], issues: list[dict]) -> dict[str, dict]:
    event_index = {e["physical_attempt_id"]: e for e in events}
    traces: dict[str, dict] = {}
    for origin in origins:
        directory = origin["directory"]
        for job in origin["bundle"]["jobs"]:
            output = relative_file(directory, job["output_path"])
            raw_directory = output.parent / (output.stem + "-raw")
            files = sorted(raw_directory.glob("response*.json")) if raw_directory.is_dir() else []
            if len(files) > MAX_RAW_TRACE_FILES_PER_JOB:
                issues.append({"code": "raw_trace_file_count_exceeded", "job_id": job["job_id"], "origin": str(directory)})
                files = files[:MAX_RAW_TRACE_FILES_PER_JOB]
            for path in files:
                try:
                    if not path.resolve().is_relative_to(directory):
                        raise ValueError("raw_trace_outside_origin")
                    with path.open("rb") as stream:
                        content = stream.read(MAX_RAW_TRACE_BYTES + 1)
                    if len(content) > MAX_RAW_TRACE_BYTES:
                        raise ValueError("raw_trace_size_exceeded")
                    raw = json.loads(content.decode("utf-8-sig"))
                    if not isinstance(raw, dict):
                        raise ValueError("raw_trace_not_object")
                    billing = raw.get("_elice_billing")
                    local = billing.get("attempt_id") if isinstance(billing, dict) else None
                    if not isinstance(local, str) or not local:
                        raise ValueError("raw_trace_billing_attempt_id_missing")
                    identifier = origin_id(directory, local)
                    event = event_index.get(identifier)
                    if event is None or event.get("job_id") != job["job_id"]:
                        raise ValueError("raw_trace_transport_attempt_unmatched")
                    summary = trace_summary(raw, path, content, event)
                    if identifier in traces:
                        issues.append({"code": "duplicate_raw_trace_attempt", "attempt_id": identifier,
                                       "identical": traces[identifier]["sha256"] == summary["sha256"]})
                        continue
                    traces[identifier] = summary
                    event["raw_trace"] = summary
                except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
                    issues.append({"code": "raw_trace_unavailable_or_unmatched", "path": str(path),
                                   "reason": str(exc) if isinstance(exc, ValueError) and str(exc).startswith("raw_trace_") else type(exc).__name__})
    return traces


def raw_diagnostics(attempts: list[dict]) -> dict:
    traces = [a["raw_trace"] for a in attempts if a.get("raw_trace")]
    known_reasoning = [t["reasoning_output_tokens"] for t in traces if t["reasoning_output_tokens"] is not None]
    known_chars = [t["visible_output_characters"] for t in traces if t["visible_output_characters"] is not None]
    non_reasoning = [t["non_reasoning_output_tokens"] for t in traces if t["non_reasoning_output_tokens"] is not None]
    write_observations = [t["raw_cache_write_observation"] for t in traces if t.get("raw_cache_write_observation")]
    validated_writes = [o for o in write_observations if o["validated_against_result_sdk_and_transport"]]
    return {"matched_raw_traces": len(traces), "raw_trace_missing_attempts": len(attempts) - len(traces),
        "raw_finish_reason_counts": dict(Counter(r for t in traces for r in t["finish_reasons"])),
        "raw_response_status_counts": dict(Counter(t["response_status"] for t in traces if t["response_status"])),
        "wire_protocol_counts": dict(Counter(t["protocol"] for t in traces if t["protocol"])),
        "truncated_attempts": sum(t["truncated"] for t in traces),
        "truncated_failed_attempts": sum(a.get("raw_trace", {}).get("truncated", False) and a["is_failed_attempt"] for a in attempts),
        "reasoning_output_tokens_known_subtotal": sum(known_reasoning),
        "reasoning_tokens_are_output_subset_not_additional_billing": True,
        "reasoning_counter_missing_attempts": len(attempts) - len(known_reasoning),
        "non_reasoning_output_tokens_known_subtotal": sum(non_reasoning),
        "visible_output_characters_known_subtotal": sum(known_chars),
        "visible_output_characters_missing_attempts": len(attempts) - len(known_chars),
        "technical_cause_counts": dict(Counter(t["technical_cause"] for t in traces)),
        "http_error_attempts": sum(type(a.get("http_status")) is int and a["http_status"] >= 400 for a in attempts),
        "http_success_but_service_failed_attempts": sum(a.get("http_status") == 200 and a.get("explicit_attempt_error", a["is_failed_attempt"]) for a in attempts),
        "http_success_attempts_in_failed_case_cost_context": sum(a.get("http_status") == 200 and a["is_failed_attempt"] for a in attempts),
        "explicit_strict_schema_incompatibility_attempts": sum(t["explicit_strict_schema_incompatibility"] for t in traces),
        "explicit_schema_request_rejection_attempts": sum(t["explicit_schema_request_rejection"] for t in traces),
        "request_cancelled_attempts": sum(a.get("technical_failure_cause") == "request_cancelled" for a in attempts),
        "attempt_technical_failure_cause_counts": dict(Counter(a["technical_failure_cause"] for a in attempts if a.get("technical_failure_cause"))),
        "service_error_stage_counts": dict(Counter(a["error_stage"] for a in attempts if a.get("explicit_attempt_error") and a.get("error_stage"))),
        "stop_finished_schema_validation_failed_attempts": sum(a.get("technical_failure_cause") == "schema_validation_failed_after_provider_stop" for a in attempts),
        "stop_finished_contract_validation_failed_attempts": sum(a.get("technical_failure_cause") == "contract_validation_failed_after_provider_stop" for a in attempts),
        "raw_top_cache_write_alias_present_attempts": sum(o["top_level_alias_present"] for o in write_observations),
        "raw_cache_write_tokens_validated_known_subtotal": sum(o["consistent_cache_write_tokens_observed"] for o in validated_writes),
        "raw_top_cache_write_tokens_validated_known_subtotal": sum(o["top_level_cache_write_tokens_observed"] for o in validated_writes if o["top_level_cache_write_tokens_observed"] is not None),
        "raw_cache_write_tokens_validated_attempts": len(validated_writes),
        "raw_cache_write_counter_conflicting_attempts": sum(bool(o["counter_conflicts"]) for o in write_observations),
        "available_nonzero_raw_write_counter_omitted_by_live_normalizer_attempts": sum(o["available_nonzero_alias_omitted_by_live_normalizer"] and o["validated_against_result_sdk_and_transport"] for o in write_observations),
        "posthoc_tariff_recalculation_performed": False,
        "interpretation": "technical protocol/limit diagnostics under the uniform cap; not approved model-quality failure"}


def load_job(origin: dict, job: dict) -> tuple[dict, dict]:
    directory = origin["directory"]
    plan = read_json(relative_file(directory, job["plan_path"]))
    result_path = relative_file(directory, job["output_path"])
    result = read_json(result_path) if result_path.exists() else {}
    return plan, result


def verified_terminal_observations(origins: list[dict]) -> dict[str, dict]:
    """A pinned missing checkpoint row is an observation, never a new output."""
    proof = origins[-1]["bundle"].get("continuation", {})
    observations = proof.get("terminal_case_observations", [])
    if not isinstance(observations, list):
        raise ValueError("terminal_case_observations_invalid")
    origins_by_directory = {str(o["directory"]): o for o in origins[:-1]}
    result = {}
    for raw in observations:
        if not isinstance(raw, dict) or raw.get("status") != "interrupted" or raw.get("retry_planned") is not False:
            raise ValueError("terminal_case_observation_state_invalid")
        if any(name not in raw or raw[name] is not None for name in
               ("input_tokens", "output_tokens", "actual_cost_usd", "output", "http_status")):
            raise ValueError("terminal_case_observation_has_invented_usage_or_output")
        if raw.get("raw_response_path") is not None:
            raise ValueError("terminal_case_observation_unexpected_response")
        source_directory = Path(raw["source_directory"]).resolve()
        origin = origins_by_directory.get(str(source_directory))
        if origin is None:
            raise ValueError("terminal_case_observation_origin_invalid")
        for path_field, hash_field in (("source_result_path", "source_result_sha256"),
                                       ("source_ledger_path", "source_ledger_sha256")):
            source = Path(raw[path_field])
            source = source.resolve() if source.is_absolute() else relative_file(source_directory, str(source))
            if not source.is_relative_to(source_directory) or hashlib.sha256(source.read_bytes()).hexdigest() != raw[hash_field]:
                raise ValueError("terminal_case_observation_source_hash_mismatch")
        job = next((j for j in origin["bundle"]["jobs"] if j["job_id"] == raw["job_id"]), None)
        if job is None or job["model_id"] != raw["model_id"]:
            raise ValueError("terminal_case_observation_job_mismatch")
        expected_paths = {"source_result_path": relative_file(source_directory, job["output_path"]),
                          "source_ledger_path": source_directory / "ledger.json"}
        for name, expected in expected_paths.items():
            actual = Path(raw[name])
            actual = actual.resolve() if actual.is_absolute() else relative_file(source_directory, str(actual))
            if actual != expected.resolve():
                raise ValueError("terminal_case_observation_source_path_mismatch")
        plan, checkpoint = load_job(origin, job)
        recorded = {case_identifier(row) for row in checkpoint.get("cases", [])}
        unresolved = [c for c in plan["selected_case_ids"] if c not in recorded]
        if not unresolved or raw["case_id"] != unresolved[0] or raw["case_id"] in recorded or checkpoint.get("run_state") not in HALTS:
            raise ValueError("terminal_case_observation_case_not_next_unresolved")
        events = [e for e in origin["ledger"].get("events", []) if e.get("event") == "settled"
                  and e.get("attempt_id") == raw["source_attempt_id"]]
        if len(events) != 1:
            raise ValueError("terminal_case_observation_attempt_unmatched")
        event = events[0]
        if (event.get("job_id") != raw["job_id"] or event.get("model") != raw["model_id"]
            or event.get("lifetime_attempt_id") != raw.get("source_lifetime_attempt_id")
            or event.get("local_attempt_id") != raw.get("source_local_attempt_id")
            or event.get("error_code") != raw.get("error_code")
            or event.get("error_code") not in {"attempt_cancelled", "request_cancelled"}
            or event.get("http_status") is not None or event.get("usage") is not None
            or any(event.get(k) is not None for k in ("input_tokens", "output_tokens", "cost_usd", "cost_lower_usd", "cost_upper_usd"))
            or money(event.get("reserved_usd")) != money(raw.get("reserved_upper_usd"))):
            raise ValueError("terminal_case_observation_event_changed")
        key = case_key(raw["model_id"], job["cases_root"], raw["case_id"])
        if key in result:
            raise ValueError("terminal_case_observation_duplicate")
        result[key] = {**raw, "physical_attempt_id": origin_id(source_directory, raw["source_attempt_id"]),
            "model_case_key": key, "source_case_row_exists": False,
            "identity_inferred": True,
            "identity_inference": "explicit pinned terminal observation; next unresolved case in source sequential plan",
            "technical_failure_cause": "request_cancelled",
            "provider_error_or_timeout_proven": False}
    return result


def verified_reused_jobs(origins: list[dict], terminal_observations: dict | None = None) -> dict[str, dict]:
    """Completed prefix outputs stay in their original immutable directories."""
    proof = origins[-1]["bundle"].get("continuation", {})
    terminal_observations = verified_terminal_observations(origins) if terminal_observations is None else terminal_observations
    references = proof.get("reused_completed_outputs", [])
    if not isinstance(references, list):
        raise ValueError("reused_completed_outputs_invalid")
    verified: dict[str, dict] = {}
    for reference in references:
        if not isinstance(reference, dict) or reference.get("job_id") in verified:
            raise ValueError("reused_completed_job_duplicate_or_invalid")
        expected_hash = reference.get("output_sha256")
        candidates = []
        for origin in origins[:-1]:
            raw_path = Path(reference["output_path"])
            path = raw_path.resolve() if raw_path.is_absolute() else relative_file(origin["directory"], str(raw_path))
            if not path.is_relative_to(origin["directory"]) or not path.is_file():
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash:
                candidates.append((origin, path))
        if len(candidates) != 1:
            raise ValueError("reused_completed_output_hash_or_origin_mismatch")
        origin, path = candidates[0]
        source_job = next((j for j in origin["bundle"]["jobs"] if j["job_id"] == reference["job_id"]), None)
        if source_job is None or source_job["model_id"] != reference["model_id"]:
            raise ValueError("reused_completed_job_identity_mismatch")
        if path != relative_file(origin["directory"], source_job["output_path"]):
            raise ValueError("reused_completed_output_job_path_mismatch")
        raw_plan = Path(reference["plan_path"])
        plan_path = raw_plan.resolve() if raw_plan.is_absolute() else relative_file(origin["directory"], str(raw_plan))
        if not plan_path.is_relative_to(origin["directory"]) or not plan_path.is_file():
            raise ValueError("reused_completed_plan_path_invalid")
        plan, result = read_json(plan_path), read_json(path)
        # Matches execution_policy.plan_digest: approval identity is the digest
        # of canonical JSON, distinct from the optional immutable file digest.
        canonical_plan = json.dumps(plan, ensure_ascii=False, allow_nan=False,
                                    sort_keys=True, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(canonical_plan).hexdigest() != reference.get("plan_sha256"):
            raise ValueError("reused_completed_plan_identity_mismatch")
        if reference.get("plan_file_sha256") and hashlib.sha256(plan_path.read_bytes()).hexdigest() != reference["plan_file_sha256"]:
            raise ValueError("reused_completed_plan_file_hash_mismatch")
        selected = reference.get("selected_case_ids")
        rows = result.get("cases", [])
        terminal_ids = {o["case_id"] for o in terminal_observations.values()
                        if o["job_id"] == reference["job_id"] and o["model_id"] == reference["model_id"]}
        recorded_ids = {case_identifier(r) for r in rows}
        partial = bool(terminal_ids)
        if (selected != plan.get("selected_case_ids") or len(rows) != len(recorded_ids)
            or recorded_ids & terminal_ids or recorded_ids | terminal_ids != set(selected or [])
            or (result.get("run_state") not in HALTS if partial else result.get("run_state") not in {"completed", "succeeded"})
            or partial and reference.get("partial_terminal") is not True
            or any(r.get("status") not in {"succeeded", "failed", "rejected"} for r in rows)):
            raise ValueError("reused_completed_output_scope_or_state_invalid")
        if reference.get("recorded_case_ids") is not None and reference["recorded_case_ids"] != [case_identifier(r) for r in rows]:
            raise ValueError("reused_completed_recorded_case_ids_mismatch")
        verified[reference["job_id"]] = {"origin": origin, "source_job": source_job,
            "result": result, "plan": plan, "reference": reference}
    declared_ids = origins[-1]["bundle"].get("reused_completed_job_ids",
                   proof.get("reused_completed_job_ids", list(verified)))
    if set(declared_ids) != set(verified):
        raise ValueError("reused_completed_job_ids_mismatch")
    return verified


def build_cases(origins: list[dict], events: list[dict], issues: list[dict]) -> tuple[list[dict], list[dict]]:
    current = origins[-1]
    terminal_observations = verified_terminal_observations(origins)
    terminal_by_attempt = {o["physical_attempt_id"]: o for o in terminal_observations.values()}
    reused = verified_reused_jobs(origins, terminal_observations)
    cases: dict[str, dict] = {}
    job_diagnostics = []
    for job in current["bundle"]["jobs"]:
        plan, result = load_job(current, job)
        fresh_result = result
        reuse = reused.get(job["job_id"])
        if reuse:
            if result.get("cases"):
                raise ValueError("reused_job_also_has_fresh_case_outputs")
            if (job["model_id"] != reuse["source_job"]["model_id"]
                or job["cases_root"] != reuse["source_job"]["cases_root"]
                or plan["selected_case_ids"] != reuse["plan"]["selected_case_ids"]):
                raise ValueError("reused_completed_job_fresh_cohort_changed")
            result = reuse["result"]
        actual: dict[str, dict] = {}
        for row in result.get("cases", []):
            identifier = case_identifier(row)
            if identifier in actual:
                issues.append({"code": "duplicate_result_case", "job_id": job["job_id"], "case_id": identifier})
            actual[identifier] = row
        selected = plan["selected_case_ids"]
        if len(set(selected)) != len(selected):
            raise ValueError("duplicate_planned_case_id")
        unexpected = sorted(set(actual) - set(selected))
        if unexpected:
            issues.append({"code": "unexpected_result_cases", "job_id": job["job_id"], "case_ids": unexpected})
        for identifier in selected:
            key = case_key(job["model_id"], job["cases_root"], identifier)
            if key in cases:
                raise ValueError("duplicate_planned_model_case")
            row = actual.get(identifier)
            terminal = terminal_observations.get(key)
            latency = case_latency(row, job["experiment"])
            cases[key] = {
                "model_case_key": key, "model_id": job["model_id"], "case_id": identifier,
                "experiment": job["experiment"], "corpus": job["cases_root"],
                "fresh_job_id": job["job_id"], "status": row.get("status", "unknown") if row else terminal["status"] if terminal else "not_executed",
                "fresh_result_present": row is not None and reuse is None,
                "display_result_present": row is not None, "result_reused": reuse is not None,
                "result_origin": str(reuse["origin"]["directory"] if reuse else current["directory"]),
                "reused_output_sha256": reuse["reference"]["output_sha256"] if reuse else None,
                "identity_inferred": bool(terminal),
                "identity_inference": terminal["identity_inference"] if terminal else None,
                "terminal_case_observation": terminal,
                **latency, "review_status": "unreviewed",
                "quality_denominator": 0, "attempts": [], "prior_attempt_ids": [],
                "fresh_attempt_ids": [], "automatic_checks": row.get("automatic_checks") if row else None,
                "_row": row, "_job": job, "_plan": plan,
            }
        job_diagnostics.append({"job_id": job["job_id"], "model_id": job["model_id"],
            "experiment": job["experiment"], "corpus": job["cases_root"],
            "run_state": result.get("run_state", "not_executed"),
            "fresh_run_state": fresh_result.get("run_state", "not_executed"),
            "result_reused": reuse is not None,
            "result_origin": str(reuse["origin"]["directory"] if reuse else current["directory"]),
            "planned_cases": len(selected), "recorded_cases": len(actual),
            "terminal_failure_observations": sum(o["job_id"] == job["job_id"] for o in terminal_observations.values()),
            "logical_terminal_cases": len(actual) + sum(o["job_id"] == job["job_id"] for o in terminal_observations.values()),
            "automatic_checks": result.get("summary", {}).get("automatic_checks"),
            "service_execution": result.get("summary", {}).get("service_execution")})

    # Match original SDK rows to physical HTTP attempts within one origin/job.
    for origin in origins:
        directory = origin["directory"]
        for job in origin["bundle"]["jobs"]:
            plan, result = load_job(origin, job)
            job_events = [e for e in events if e["origin"] == str(directory) and e.get("job_id") == job["job_id"]]
            available = list(job_events)
            rows = result.get("cases", [])
            selected = plan["selected_case_ids"]
            for row in rows:
                identifier = case_identifier(row)
                key = case_key(job["model_id"], job["cases_root"], identifier)
                target = cases.get(key)
                if target is None:
                    issues.append({"code": "historical_case_outside_fresh_cohort", "case_key": key})
                    continue
                seen_task_stages: Counter = Counter()
                for index, sdk in enumerate(row.get("attempts", []), 1):
                    sdk_id = f"{directory.as_posix()}::{job['job_id']}::{identifier}::sdk-{index}"
                    response_id = sdk.get("response_id")
                    matches = [e for e in available if response_id and e.get("response_id") == response_id]
                    event = None
                    match_method = None
                    if len(matches) == 1:
                        event = matches[0]
                        match_method = "response_id"
                    elif len(matches) > 1:
                        issues.append({"code": "ambiguous_response_id", "sdk_attempt_id": sdk_id})
                    elif not response_id and available:
                        # Missing response IDs are common on errors; same-job order is
                        # the only supported fallback. It is always disclosed.
                        event = available[0]
                        match_method = "same_job_sequential"
                    else:
                        issues.append({"code": "sdk_attempt_without_transport_match", "sdk_attempt_id": sdk_id,
                                       "response_id": response_id})
                    if event is not None:
                        available.remove(event)
                        event["linked_case_key"] = key
                        event["linked_sdk_attempt_id"] = sdk_id
                    attempt = make_attempt(event, sdk, sdk_id, match_method, target, origin["role"], issues)
                    attempt["origin_case_status"] = row.get("status")
                    if row.get("status") in FAILURES:
                        attempt["is_failed_attempt"] = True
                        attempt["failed_case_cost_context"] = True
                    classify_retry(attempt, sdk, job["experiment"], seen_task_stages)
                    target["attempts"].append(attempt)
                    target["prior_attempt_ids" if origin["role"] == "parent" else "fresh_attempt_ids"].append(attempt["physical_attempt_id"])

            if not available:
                continue
            actual_ids = {case_identifier(r) for r in rows}
            unresolved = [identifier for identifier in selected if identifier not in actual_ids]
            in_progress = result.get("in_progress_case")
            if isinstance(in_progress, dict):
                in_progress = in_progress.get("case_id")
            if isinstance(in_progress, str):
                in_progress = in_progress.rsplit(".v", 1)[0]
            inference = None
            if in_progress in selected:
                inference = "explicit_in_progress_checkpoint"
            elif unresolved and result.get("run_state") in HALTS:
                in_progress = unresolved[0]
                inference = "first_unrecorded_case_in_sequential_plan"
            else:
                in_progress = None
            proof = current["bundle"].get("continuation", {})
            explicit_first_job = proof.get("first_job_id")
            explicit_first_case = proof.get("first_case_id")
            if origin["role"] == "parent" and len(available) == 1 and (
                job["job_id"] == explicit_first_job or (not explicit_first_job and job is origin["bundle"]["jobs"][0])
            ):
                in_progress = explicit_first_case or selected[0]
                inference = "continuation_first_case_proof" if explicit_first_case else "parent_first_case_sequential_plan"
            for event in available:
                terminal = terminal_by_attempt.get(event["physical_attempt_id"])
                key = terminal["model_case_key"] if terminal else case_key(job["model_id"], job["cases_root"], in_progress) if in_progress else None
                event_inference = terminal["identity_inference"] if terminal else inference
                target = cases.get(key)
                if target is None:
                    issues.append({"code": "orphan_transport_attempt", "attempt_id": event["physical_attempt_id"],
                                   "job_id": job["job_id"]})
                    continue
                event["linked_case_key"] = key
                event["identity_inference"] = event_inference
                attempt = make_attempt(event, None, None, "orphan_identity_inferred", target, origin["role"], issues)
                attempt["identity_inference"] = event_inference
                if terminal:
                    attempt["terminal_case_observation"] = terminal
                target["attempts"].append(attempt)
                target["prior_attempt_ids" if origin["role"] == "parent" else "fresh_attempt_ids"].append(attempt["physical_attempt_id"])
                if origin["role"] == "fresh" and not target["fresh_result_present"]:
                    target.update(status="interrupted", identity_inferred=True, identity_inference=inference)

    for row in cases.values():
        row["prior_orphan_attempt_present"] = any(a["origin_role"] == "parent" and a["sdk_attempt_id"] is None for a in row["attempts"])
        row["lifetime_attempted"] = bool(row["attempts"])
        row["fresh_attempted"] = bool(row["fresh_attempt_ids"])
        prior_unknown = [a["physical_attempt_id"] for a in row["attempts"]
                         if a["origin_role"] == "parent" and a["cost_status"] == "unknown"]
        fresh_attempts = [a for a in row["attempts"] if a["origin_role"] == "fresh"]
        if prior_unknown and fresh_attempts:
            fresh_attempts[0]["infrastructure_retry_context"] = {
                "prior_unknown_attempt_ids": prior_unknown,
                "basis": "same planned case rerun after prior startup failures",
                "does_not_change_routine_task_retry_flag": True,
                "prior_usage_and_actual_cost_remain_unknown": True}
    # A failed join may represent the same physical request on both sides.
    # Keep both observations visible, but never add its orphan transport tokens
    # to already-observed SDK tokens for that job and call the result a total.
    unmatched_jobs = {(a["origin"], a["job_id"]) for c in cases.values() for a in c["attempts"]
                      if a["sdk_attempt_id"] is not None and a["match_method"] is None}
    for row in cases.values():
        for attempt in row["attempts"]:
            if attempt["sdk_attempt_id"] is None and (attempt["origin"], attempt["job_id"]) in unmatched_jobs:
                attempt["tokens_excluded_from_subtotal_due_to_ambiguous_join"] = True
        row["cost"] = aggregate_cost(row["attempts"])
        row["tokens"] = aggregate_tokens(row["attempts"])
    return list(cases.values()), job_diagnostics


def event_tokens(event: dict | None, name: str) -> int | None:
    if not event:
        return None
    raw = event.get("usage")
    value = raw.get(name) if isinstance(raw, dict) else event.get(name)
    return token(value)


def classify_retry(attempt: dict, sdk: dict, experiment: str, seen_stages: Counter) -> None:
    """Director's planned second call is a review, not a repeated attempt.

    Actual A result rows number plan=1/review=2 consecutively. Task schema gives
    the explicit stage identity; only another call to the same stage is retry.
    B's attempt counter already represents retries of its single score task.
    """
    schema = sdk.get("schema_version")
    stage = next((name for name in ("director-plan", "director-review")
                  if isinstance(schema, str) and schema.startswith(name + ".")), None)
    attempt["task_schema_version"] = schema
    attempt["task_prompt_version"] = sdk.get("prompt_version")
    attempt["intentional_director_review"] = False
    attempt["retry_classification_basis"] = "SDK attempt_number > 1"
    if experiment == "A" and stage:
        seen_stages[stage] += 1
        attempt["is_retry"] = seen_stages[stage] > 1
        attempt["task_stage"] = stage
        attempt["task_stage_attempt_number"] = seen_stages[stage]
        attempt["intentional_director_review"] = stage == "director-review" and seen_stages[stage] == 1
        attempt["retry_classification_basis"] = "repeated Director task stage; planned review excluded"
    elif experiment == "A":
        attempt["retry_classification_ambiguous"] = True
    attempt["retry_or_failure"] = attempt["is_retry"] or attempt["is_failed_attempt"]


def make_attempt(event: dict | None, sdk: dict | None, sdk_id: str | None,
                 method: str | None, case: dict, role: str, issues: list[dict]) -> dict:
    event = event or {}
    inputs = token(sdk.get("input_tokens")) if sdk is not None else event_tokens(event, "input_tokens")
    outputs = token(sdk.get("output_tokens")) if sdk is not None else event_tokens(event, "output_tokens")
    mismatch = []
    for name, value in (("input_tokens", inputs), ("output_tokens", outputs)):
        observed = event_tokens(event, name)
        if sdk is not None and value is not None and observed is not None and value != observed:
            mismatch.append(name)
    if mismatch:
        issues.append({"code": "sdk_transport_token_mismatch", "sdk_attempt_id": sdk_id, "fields": mismatch})
    sdk_complete = sdk is not None and inputs is not None and outputs is not None
    lower, upper, exact = (money(event.get(name)) for name in ("cost_lower_usd", "cost_upper_usd", "cost_usd"))
    valid_bounds = lower is not None and upper is not None and lower <= upper
    exact_valid = (exact is not None and event.get("cost_status") == "confirmed"
                   and valid_bounds and lower == exact == upper)
    valid = bool(event and event.get("settled") and sdk_complete and not mismatch and valid_bounds)
    status = "confirmed" if valid and exact_valid else "bounded" if valid and event.get("cost_status") in {"bounded", "confirmed"} else "unknown"
    if event.get("_conflicting_duplicate"):
        status = "unknown"
    number = sdk.get("attempt") if sdk else None
    retry = type(number) is int and number > 1
    errored = bool((sdk and (sdk.get("error_stage") or sdk.get("error_code"))) or event.get("error_code"))
    failed = errored or (case["status"] in FAILURES and role == "fresh") or (role == "parent" and sdk is None)
    cancelled = event.get("error_code") in {"attempt_cancelled", "request_cancelled"}
    return {
        "physical_attempt_id": event.get("physical_attempt_id", f"unmatched::{sdk_id}"),
        "lifetime_attempt_id": event.get("lifetime_attempt_id"),
        "local_attempt_id": event.get("attempt_id"), "sdk_attempt_id": sdk_id,
        "origin": event.get("origin") or (sdk_id.rsplit("::", 3)[0] if sdk_id else None), "origin_role": role,
        "job_id": event.get("job_id", case["fresh_job_id"]),
        "response_id": event.get("response_id") or (sdk.get("response_id") if sdk else None),
        "match_method": method, "sdk_attempt_number": number,
        "sdk_token_totals_complete": sdk_complete,
        "token_source": "result_case_attempt" if sdk is not None else "transport_orphan_observation",
        "input_tokens": inputs, "output_tokens": outputs,
        "transport_input_tokens": event_tokens(event, "input_tokens"),
        "transport_output_tokens": event_tokens(event, "output_tokens"),
        "transport_usage": event.get("usage"), "token_mismatch_fields": mismatch,
        "cost_status": status, "transport_cost_status": event.get("cost_status"),
        "cost_usd": str(exact) if status == "confirmed" else None,
        "cost_lower_usd": str(lower) if valid_bounds else None,
        "cost_upper_usd": str(upper) if valid_bounds else None,
        "transport_cost_usd": str(exact) if exact is not None else None,
        "transport_reserved_usd": event.get("reserved_usd"),
        "http_status": event.get("http_status"), "sent": event.get("sent"),
        "error_code": (sdk.get("error_code") if sdk else None) or event.get("error_code"),
        "error_stage": sdk.get("error_stage") if sdk else None,
        "latency_ms": finite_number(sdk.get("latency_ms")) if sdk else None,
        "is_retry": retry, "is_failed_attempt": failed,
        "explicit_attempt_error": errored,
        "failed_case_cost_context": case["status"] in FAILURES and role == "fresh",
        "technical_failure_cause": "request_cancelled" if cancelled else None,
        "provider_error_or_timeout_proven": False if cancelled else None,
        "retry_or_failure": retry or failed,
        "unknown_reason": None if status != "unknown" else (
            "sdk_transport_tokens_differ" if mismatch else "result_case_attempt_usage_missing" if not sdk_complete
            else "transport_accounting_unconfirmed"),
    }


def aggregate_tokens(attempts: list[dict]) -> dict:
    eligible = [a for a in attempts if not a.get("tokens_excluded_from_subtotal_due_to_ambiguous_join")]
    excluded = len(attempts) - len(eligible)
    missing_input = excluded + sum(token(a.get("input_tokens")) is None for a in eligible)
    missing_output = excluded + sum(token(a.get("output_tokens")) is None for a in eligible)
    inputs = sum(a["input_tokens"] for a in eligible if token(a.get("input_tokens")) is not None)
    outputs = sum(a["output_tokens"] for a in eligible if token(a.get("output_tokens")) is not None)
    reconciled = not any(a.get("match_method") is None or a.get("token_mismatch_fields") for a in attempts)
    return {"input_known_subtotal": inputs, "output_known_subtotal": outputs,
        "input_total": inputs if attempts and not missing_input and reconciled else None,
        "output_total": outputs if attempts and not missing_output and reconciled else None,
        "missing_input_attempts": missing_input, "missing_output_attempts": missing_output,
        "result_sdk_usage_missing_attempts": sum(not a.get("sdk_token_totals_complete") for a in attempts),
        "known_subtotal_includes_identified_transport_orphans": any(a.get("token_source") == "transport_orphan_observation" for a in attempts),
        "unmatched_sdk_attempts": sum(a.get("match_method") is None for a in attempts),
        "ambiguous_orphan_observations_excluded_from_subtotal": excluded,
        "known_subtotal_reconciliation_complete": reconciled}


def aggregate_cost(attempts: list[dict]) -> dict:
    unknown = sum(a.get("cost_status") == "unknown" for a in attempts)
    bounded = sum(a.get("cost_status") == "bounded" for a in attempts)
    exact = sum((money(a.get("cost_usd")) or ZERO for a in attempts), ZERO)
    lower = sum((money(a.get("cost_lower_usd")) or ZERO for a in attempts), ZERO)
    upper = sum((money(a.get("cost_upper_usd")) or ZERO for a in attempts), ZERO)
    status = "not_executed" if not attempts else "unknown" if unknown else "bounded" if bounded else "confirmed"
    return {"status": status, "cost_usd": str(exact) if status == "confirmed" else None,
        "cost_lower_usd": str(lower) if attempts and not unknown else None,
        "cost_upper_usd": str(upper) if attempts and not unknown else None,
        "known_confirmed_subtotal_usd": str(exact),
        "known_tariff_lower_subtotal_usd": str(lower), "known_tariff_upper_subtotal_usd": str(upper),
        "unknown_attempts": unknown, "bounded_attempts": bounded, "attempts": len(attempts)}


def divide_cost(cost: dict, denominator: int, label: str) -> dict:
    return {"denominator": denominator, "denominator_label": label,
        "status": cost["status"] if denominator else "unavailable",
        **{name: str(Decimal(cost[name]) / denominator) if denominator and cost.get(name) is not None else None
           for name in ("cost_usd", "cost_lower_usd", "cost_upper_usd")}}


def waste_cost(attempts: list[dict]) -> dict:
    wasted = [a for a in attempts if a["retry_or_failure"]]
    other = [a for a in attempts if not a["retry_or_failure"]]
    total, part = aggregate_cost(attempts), aggregate_cost(wasted)
    other_cost = aggregate_cost(other)
    exact_ratio = None
    if total["status"] == "confirmed" and Decimal(total["cost_usd"]) > 0:
        exact_ratio = str(Decimal(part["cost_usd"] or "0") / Decimal(total["cost_usd"]))
    lower_ratio = upper_ratio = None
    if not total["unknown_attempts"] and attempts:
        wl = Decimal(part["cost_lower_usd"] or "0")
        wu = Decimal(part["cost_upper_usd"] or "0")
        nl = Decimal(other_cost["cost_lower_usd"] or "0")
        nu = Decimal(other_cost["cost_upper_usd"] or "0")
        lower_ratio = str(wl / (wl + nu)) if wl + nu > 0 else None
        upper_ratio = str(wu / (wu + nl)) if wu + nl > 0 else None
    known_total = Decimal(total["known_tariff_upper_subtotal_usd"])
    known_part = Decimal(part["known_tariff_upper_subtotal_usd"])
    return {"definition": "union(B attempt_number>1 or repeated A task stage, error_stage/error_code, attempt in failed/interrupted case); planned A review excluded; each physical attempt once",
        "attempts": len(wasted), "cost": part, "actual_cost_ratio": exact_ratio,
        "actual_cost_ratio_lower": lower_ratio, "actual_cost_ratio_upper": upper_ratio,
        "known_upper_subtotal_ratio_diagnostic": str(known_part / known_total) if known_total else None,
        "known_upper_subtotal_ratio_is_actual_cost": False}


def new_b_metrics() -> dict:
    return {"planned_interviews": 0, "scored_interviews": 0, "expected_pairs": 0,
        "compared_pairs": 0, "unavailable_pairs": 0, "strict_matches": 0,
        "acceptable_matches": 0, "target_na_pairs": 0, "compared_target_na_pairs": 0,
        "predicted_na_pairs": 0, "na_matches": 0, "na_mismatches": 0,
        "numeric_pairs_compared": 0, "numeric_absolute_error_sum": 0,
        "numeric_stage_mae": None, "service_total_absolute_deviation_mean": None,
        "service_key_absolute_deviation_mean": None, "service_scores": [],
        "diagnostic_errors": [], "review_status": "unreviewed", "approved_accuracy_denominator": 0,
        "interpretation": "unreviewed draft agreement; not approved correctness"}


def service_score_function(lab: Path, devon: Path):
    sys.path.insert(0, str(lab))
    from lab_paths import attach_devon
    attach_devon(devon)
    from devon_ai import contracts
    from devon_ai.llm_tasks.report import _build_inputs
    from devon_ai.report_scores import compute_scores

    def evaluate(raw, service_input):
        turns, _, _ = _build_inputs(service_input)
        checked = contracts.validate_score_judgments(
            contracts.decode_strict(contracts.ScoreJudgments, raw), turns=turns)
        result = compute_scores(checked)
        return {"keys": dict(result.key_scores), "total": result.total_score}
    return evaluate


def diagnose_b(cases: list[dict], lab: Path, score_function) -> dict[str, dict]:
    metrics = {"main": new_b_metrics(), "legacy_na": new_b_metrics()}
    for case in cases:
        if case["experiment"] != "B":
            continue
        group = "legacy_na" if "legacy" in case["corpus"] else "main"
        metric = metrics[group]
        metric["planned_interviews"] += 1
        root = (lab / case["corpus"]).resolve()
        if not root.is_relative_to(lab):
            raise ValueError("case_corpus_outside_lab")
        gold = read_json(root / "gold" / f"{case['case_id']}.json")
        expected = {(str(g["turn_id"]), g["key"]): g for g in gold}
        metric["expected_pairs"] += len(expected)
        metric["target_na_pairs"] += sum(g["level"] == "not_applicable" for g in gold)
        row = case["_row"]
        if not row or case["status"] != "succeeded":
            continue
        try:
            output = row["output"]
            judgments = output["judgments"]
            predictions = {(str(p["turn_id"]), p["key"]): p["level"] for p in judgments}
            if len(predictions) != len(judgments) or set(predictions) != set(expected):
                raise ValueError("diagnostic_pair_mismatch")
            if any(not (type(v) is int and v >= 0 or v == "not_applicable") for v in predictions.values()):
                raise ValueError("diagnostic_invalid_level")
            # Use the actual selected input version rather than silently inventing
            # a version. The fixed campaign has exactly one matching input file.
            candidates = list((root / "inputs").glob(f"{case['case_id']}.v*.json"))
            if len(candidates) != 1:
                raise ValueError("diagnostic_input_version_ambiguous")
            envelope = read_json(candidates[0])
            service_input = envelope["payload"]["service_input"]
            actual_scores = score_function(output, service_input)
            draft_scores = score_function({"judgments": [
                {"turn_id": g["turn_id"], "key": g["key"], "level": g["level"]} for g in gold]}, service_input)
            key_errors = [abs(actual_scores["keys"][k] - draft_scores["keys"][k]) for k in draft_scores["keys"]]
        except Exception as exc:
            # Retain the case and its planned pairs if its diagnostic is invalid.
            metric["diagnostic_errors"].append({"case_id": case["case_id"], "error": type(exc).__name__,
                                                 "code": str(exc)[:180]})
            continue
        per_case = {"expected_pairs": len(expected), "strict_matches": 0, "acceptable_matches": 0,
                    "na_mismatches": 0, "numeric_pairs_compared": 0, "numeric_absolute_error_sum": 0}
        for key, draft in expected.items():
            prediction, target = predictions[key], draft["level"]
            metric["compared_pairs"] += 1
            strict = prediction == target
            acceptable = prediction in draft.get("acceptable", [target])
            mismatch = (prediction == "not_applicable") != (target == "not_applicable")
            for destination in (metric, per_case):
                destination["strict_matches"] += strict
                destination["acceptable_matches"] += acceptable
                destination["na_mismatches"] += mismatch
                if type(prediction) is int and type(target) is int:
                    destination["numeric_pairs_compared"] += 1
                    destination["numeric_absolute_error_sum"] += abs(prediction - target)
            metric["compared_target_na_pairs"] += target == "not_applicable"
            metric["predicted_na_pairs"] += prediction == "not_applicable"
            metric["na_matches"] += prediction == target == "not_applicable"
        total_deviation = abs(actual_scores["total"] - draft_scores["total"])
        score_row = {"case_id": case["case_id"], "corpus": case["corpus"],
            "predicted": actual_scores, "draft_reference": draft_scores,
            "absolute_total_deviation": total_deviation, "key_absolute_deviations": key_errors}
        metric["service_scores"].append(score_row)
        metric["scored_interviews"] += 1
        case["B_draft_diagnostic"] = {**per_case, **score_row, "approved_correctness": False}
    for metric in metrics.values():
        metric["unavailable_pairs"] = metric["expected_pairs"] - metric["compared_pairs"]
        numeric = metric["numeric_pairs_compared"]
        metric["numeric_stage_mae"] = metric["numeric_absolute_error_sum"] / numeric if numeric else None
        scores = metric["service_scores"]
        metric["service_total_absolute_deviation_mean"] = sum(s["absolute_total_deviation"] for s in scores) / len(scores) if scores else None
        key_errors = [v for s in scores for v in s["key_absolute_deviations"]]
        metric["service_key_absolute_deviation_mean"] = sum(key_errors) / len(key_errors) if key_errors else None
    return metrics


def orphan_attempt(event: dict) -> dict:
    """Unidentified physical attempts still count against their model/global cost."""
    dummy = {"status": "interrupted", "fresh_job_id": event.get("job_id")}
    return make_attempt(event, None, None, "unidentified_transport_orphan", dummy, event["origin_role"], [])


def analyze(directory: Path) -> tuple[dict, dict]:
    directory = directory.resolve()
    origins = load_origin_chain(directory)
    fresh = origins[-1]
    proof = fresh["bundle"].get("continuation")
    if not isinstance(proof, dict) or not proof.get("parent_directory"):
        raise ValueError("continuation_parent_directory_missing")
    parent_path = Path(proof["parent_directory"])
    if not parent_path.is_absolute():
        parent_path = directory / parent_path
    parent_path = parent_path.resolve()
    if parent_path == directory:
        raise ValueError("continuation_parent_is_current_run")
    issues: list[dict] = []
    events = collect_transport(origins, issues)
    cases, jobs = build_cases(origins, events, issues)
    if len(cases) != 96 or any(sum(c["model_id"] == m for c in cases) != 16 for m in MODELS):
        raise ValueError("fresh_fixed_96_model_case_cohort_mismatch")
    event_by_id = {e["physical_attempt_id"]: e for e in events}
    attempts = [a for case in cases for a in case["attempts"]]
    attempts.extend(orphan_attempt(e) for e in events if e["linked_case_key"] is None)
    unmatched_jobs = {(a["origin"], a["job_id"]) for a in attempts
                      if a["sdk_attempt_id"] is not None and a["match_method"] is None}
    for attempt in attempts:
        if attempt["sdk_attempt_id"] is None and (attempt["origin"], attempt["job_id"]) in unmatched_jobs:
            attempt["tokens_excluded_from_subtotal_due_to_ambiguous_join"] = True
    if len({a["physical_attempt_id"] for a in attempts}) != len(attempts):
        raise ValueError("physical_attempt_accounted_more_than_once")
    matched_events = {a["physical_attempt_id"] for a in attempts if a["physical_attempt_id"] in event_by_id}
    if matched_events != set(event_by_id):
        raise ValueError("transport_attempt_accounting_count_mismatch")
    traces = collect_raw_traces(origins, events, issues)
    for attempt in attempts:
        trace = traces.get(attempt["physical_attempt_id"])
        if trace:
            enrich_attempt_with_raw_trace(attempt, trace)
    inherited = [e for e in events if e["origin_role"] == "parent"]
    declared_inherited = proof.get("inherited_attempts", len(inherited))
    if len(inherited) != declared_inherited:
        issues.append({"code": "inherited_attempt_count_mismatch", "declared": declared_inherited, "observed": len(inherited)})
    hold = money(proof.get("inherited_unknown_hold_usd"))
    if hold is None:
        raise ValueError("continuation_inherited_hold_missing")
    lab = Path(fresh["bundle"].get("lab_root") or "C:/Users/dreac/Desktop/kdt/model-lab").resolve()
    devon = Path(fresh["bundle"].get("devon_root") or lab.parent / "devon").resolve()
    score_function = service_score_function(lab, devon)
    inherited_hold_by_model = {model: sum((money(e.get("reserved_usd")) or ZERO for e in inherited
        if e.get("model") == model and money(e.get("cost_upper_usd")) is None), ZERO) for model in MODELS}
    allocated_hold = sum(inherited_hold_by_model.values(), ZERO)
    if allocated_hold != hold:
        issues.append({"code": "inherited_unknown_hold_reservation_sum_mismatch",
                       "declared_hold_usd": str(hold), "observed_unknown_reservations_usd": str(allocated_hold)})
    models = []
    for model in MODELS:
        selected = [c for c in cases if c["model_id"] == model]
        physical = [a for a in attempts if (event_by_id.get(a["physical_attempt_id"], {}).get("model") or next((c["model_id"] for c in selected if a in c["attempts"]), None)) == model]
        cost = aggregate_cost(physical)
        tokens = aggregate_tokens(physical)
        statuses = Counter(c["status"] for c in selected)
        fresh_executed = sum(c["fresh_attempted"] or c["fresh_result_present"] for c in selected)
        executed = sum(c["lifetime_attempted"] or c["display_result_present"] for c in selected)
        failed = sum(c["status"] in FAILURES for c in selected)
        fresh_failed = sum(c["status"] in FAILURES and not c["result_reused"] for c in selected)
        latency = [c["latency_ms"] for c in selected if c["latency_ms"] is not None]
        b_cases = [c for c in selected if c["experiment"] == "B"]
        b_attempts = [a for c in b_cases for a in c["attempts"]]
        b_cost = aggregate_cost(b_attempts)
        b_metrics = diagnose_b(selected, lab, score_function)
        raw_metrics = raw_diagnostics(physical)
        strict_schema_blocked = (raw_metrics["explicit_strict_schema_incompatibility_attempts"] > 0
                                 and not any(c["status"] == "succeeded" for c in selected))
        quality_status = "not_evaluated_strict_schema_incompatible" if strict_schema_blocked else "unreviewed_draft_diagnostic_only"
        for diagnostic in b_metrics.values():
            diagnostic["strict_match_count_observed"] = diagnostic["strict_matches"]
            diagnostic["acceptable_match_count_observed"] = diagnostic["acceptable_matches"]
            diagnostic["evaluation_status"] = quality_status
            diagnostic["agreement_denominator"] = diagnostic["compared_pairs"]
            diagnostic["strict_agreement_rate"] = (diagnostic["strict_matches"] / diagnostic["compared_pairs"]
                if diagnostic["compared_pairs"] and not strict_schema_blocked else None)
            diagnostic["acceptable_agreement_rate"] = (diagnostic["acceptable_matches"] / diagnostic["compared_pairs"]
                if diagnostic["compared_pairs"] and not strict_schema_blocked else None)
            if strict_schema_blocked:
                diagnostic["strict_matches"] = None
                diagnostic["acceptable_matches"] = None
                diagnostic["interpretation"] = "not evaluated: provider explicitly rejected strict response_format under this proxy; zero compared pairs is not zero accuracy"
        for case in selected:
            case["quality_evaluation_status"] = quality_status
        strict = sum(v["strict_match_count_observed"] for v in b_metrics.values())
        attempted = sum(c["lifetime_attempted"] for c in selected)
        b_attempted = sum(c["lifetime_attempted"] for c in b_cases)
        models.append({"model_id": model, "planned_cases": len(selected),
            **raw_metrics,
            "quality_evaluation_status": quality_status,
            "strict_schema_compatibility": "explicitly_rejected_by_provider_under_this_proxy" if strict_schema_blocked else "no_explicit_rejection_observed",
            "quality_failure_rate": None,
            "case_statuses": dict(statuses), "fresh_executed_cases": fresh_executed,
            "executed_cases_including_reused_completed": executed,
            "reused_completed_cases": sum(c["result_reused"] and c["display_result_present"] for c in selected),
            "reused_terminal_failure_observations": sum(c["terminal_case_observation"] is not None for c in selected),
            "recorded_source_case_rows": sum(c["display_result_present"] for c in selected),
            "lifetime_attempted_cases": attempted, "unknown_cost_cases": sum(c["cost"]["status"] == "unknown" for c in selected),
            "technical_failures": failed, "failure_rate_executed": failed / executed if executed else None,
            "technical_failure_rate_executed": failed / executed if executed else None,
            "failure_rate_executed_interpretation": "technical execution outcomes; not a model quality failure rate",
            "failure_rate_fresh_executed": fresh_failed / fresh_executed if fresh_executed else None,
            "latency_ms": {"p50": percentile(latency, .5), "p95": percentile(latency, .95), "measured_cases": len(latency),
                "source_counts": dict(Counter(c["latency_source"] for c in selected)),
                "failed_zero_placeholders_replaced": sum(c["latency_source"] == "sdk_attempt_sum_replacing_failed_service_zero_placeholder" for c in selected)},
            "physical_attempts": sum(a["physical_attempt_id"] in event_by_id for a in physical),
            "accounting_attempt_records": len(physical),
            "sent_http_attempts": sum(a["sent"] is True for a in physical),
            "cost": cost, "tokens": tokens,
            "prior_unknown_reservation_hold_usd": str(inherited_hold_by_model[model]),
            "average_cost_per_attempted_case": divide_cost(cost, attempted, "lifetime model-case pairs with an attempt"),
            "average_cost_per_attempted_interview": divide_cost(b_cost, b_attempted, "B interviews with an attempt; B costs only"),
            "cost_per_strict_B_draft_pair_match_diagnostic": {
                **divide_cost(b_cost, strict, "strict matches to unreviewed B draft pairs; B costs only"),
                "approved_correctness": False},
            "retry_or_failure_cost": waste_cost(physical),
            "A_technical": {"planned_cases": sum(c["experiment"] == "A" for c in selected),
                "quality_evaluation_status": quality_status,
                "technical_valid_cases": sum(c["experiment"] == "A" and c["status"] == "succeeded" for c in selected),
                "technical_validity_basis": "original service succeeded with its schema validation; no semantic judge",
                "service_succeeded_cases": sum(c["experiment"] == "A" and c["status"] == "succeeded" for c in selected),
                "automatic_checks_by_job": [j for j in jobs if j["model_id"] == model and j["experiment"] == "A"],
                "semantic_judge": "not_run", "semantic_accuracy": None},
            "B_draft_diagnostic": b_metrics,
            "review_status": "unreviewed", "approved_accuracy_denominator": 0})
    all_cost = aggregate_cost(attempts)
    known_upper = sum((money(e.get("cost_upper_usd")) or ZERO for e in events), ZERO)
    active_upper = sum((money(e.get("cost_upper_usd")) or ZERO for e in events if e["origin_role"] == "fresh"), ZERO)
    inherited_upper = known_upper - active_upper
    unresolved_fresh = [e for e in events if e["origin_role"] == "fresh" and money(e.get("cost_upper_usd")) is None]
    unknown_fresh_reserved = sum((money(e.get("reserved_usd")) or ZERO for e in unresolved_fresh), ZERO)
    unknown_original = [a for c in cases if c["prior_orphan_attempt_present"] for a in c["attempts"] if a["origin_role"] == "parent"]
    first404 = next((e for e in events if e["origin_role"] == "parent" and e.get("http_status") == 404
                     and e.get("model") == "gpt-6.1-sol"), None)
    expected_first_key = case_key("gpt-6.1-sol", "cases/question/benchmark-v1", "a-dev-0001")
    first_case = next((c for c in cases if c["model_case_key"] == expected_first_key), None)
    budget = fresh["campaign"].get("global_budget", fresh["ledger"].get("global_budget", {}))
    conservative_exposure = known_upper + hold + unknown_fresh_reserved
    budget_limit = money(budget.get("amount_usd")) or Decimal("10")
    parent_missing = sum(not a["sdk_token_totals_complete"] for a in attempts if a["origin_role"] == "parent")
    report = {"version": 1, "run_directory": str(directory), "parent_directory": str(parent_path),
        "ancestor_directories": [str(o["directory"]) for o in origins[:-1]],
        "run_state": fresh["campaign"].get("run_state", fresh["ledger"].get("run_state", "unknown")),
        "run_error": fresh["campaign"].get("run_error"), "global_budget": budget,
        "planned_model_case_pairs": len(cases), "case_statuses": dict(Counter(c["status"] for c in cases)),
        "source_recorded_cases": sum(c["display_result_present"] for c in cases),
        "recorded_cases": sum(c["display_result_present"] for c in cases),
        "source_failed_cases": sum(c["display_result_present"] and c["status"] in {"failed", "rejected"} for c in cases),
        "logical_failed_cases": sum(c["status"] in {"failed", "rejected", "interrupted"} for c in cases),
        "fresh_recorded_cases": sum(c["fresh_result_present"] for c in cases),
        "reused_recorded_cases": sum(c["result_reused"] and c["display_result_present"] for c in cases),
        "logical_terminal_cases": sum(c["status"] in {"succeeded", "failed", "rejected", "interrupted"} for c in cases),
        "terminal_failure_observations": sum(c["terminal_case_observation"] is not None for c in cases),
        "terminal_interrupted_observations": sum(c["terminal_case_observation"] is not None for c in cases),
        "terminal_case_observations": [c["terminal_case_observation"] for c in cases if c["terminal_case_observation"] is not None],
        "cost": all_cost, "tokens": aggregate_tokens(attempts),
        "raw_response_diagnostics": raw_diagnostics(attempts),
        "exact_cost_total_usd": all_cost["cost_usd"],
        "known_transport_tariff_upper_subtotal_usd": str(known_upper),
        "known_fresh_transport_upper_debit_usd": str(active_upper),
        "known_inherited_transport_upper_debit_usd": str(inherited_upper),
        "inherited_unknown_reservation_hold_usd": str(hold),
        "inherited_unknown_hold_by_model_usd": {model: str(value) for model, value in inherited_hold_by_model.items()},
        "unallocated_inherited_unknown_hold_usd": str(hold - allocated_hold),
        "known_lifetime_budget_exposure_usd": str(known_upper + hold),
        "lifetime_budget_exposure_is_actual_invoice": False,
        "additional_unpriced_fresh_attempts": len(unresolved_fresh),
        "additional_unpriced_fresh_reservation_subtotal_usd": str(unknown_fresh_reserved),
        "known_upper_plus_all_unknown_reservations_usd": str(known_upper + hold + unknown_fresh_reserved),
        "all_unknown_reservations_usd": str(hold + unknown_fresh_reserved),
        "conservative_budget_exposure_including_all_unknown_reservations_usd": str(conservative_exposure),
        "conservative_budget_exposure_is_actual_cost": False,
        "budget_limit_usd": str(budget_limit),
        "conservative_reservation_margin_usd": str(budget_limit - conservative_exposure),
        "stopped_for_budget_exhaustion": conservative_exposure >= budget_limit,
        "explicit_strict_schema_rejected_models": [m["model_id"] for m in models if m["quality_evaluation_status"] == "not_evaluated_strict_schema_incompatible"],
        "full_lifetime_exposure_upper_usd": str(known_upper + hold) if not unresolved_fresh and allocated_hold == hold else None,
        "unknown_cost_cases": sum(c["cost"]["status"] == "unknown" for c in cases),
        "physical_attempts": len(events), "accounting_attempt_records": len(attempts), "transport_attempts": len(events),
        "parent_attempts": len(inherited), "fresh_transport_attempts": len(events) - len(inherited),
        "original_unknown_attempt_preserved": bool(unknown_original) and parent_missing > 0,
        "first_case_lifetime_cost_remains_unknown": bool(first_case and first_case["cost"]["status"] == "unknown"),
        "original_first404": None if first404 is None else {
            "physical_attempt_id": first404["physical_attempt_id"], "http_status": first404["http_status"],
            "linked_case_key": first404["linked_case_key"], "identity_inference": first404.get("identity_inference"),
            "exact_expected_first_case": first404["linked_case_key"] == expected_first_key,
            "actual_cost_usd": None, "actual_cost_status": "unknown"},
        "transport_unidentified_orphan_attempts": sum(e["linked_case_key"] is None for e in events),
        "reconciliation": {"issues": issues, "issue_count": len(issues),
            "origin_qualified_ids": True, "result_attempts": sum(a["sdk_attempt_id"] is not None for a in attempts),
            "result_attempts_without_transport": sum(a["sdk_attempt_id"] is not None and a["physical_attempt_id"] not in event_by_id for a in attempts),
            "transport_attempts_without_result_sdk_row": sum(e["linked_sdk_attempt_id"] is None for e in events),
            "all_transport_attempts_accounted_once": True},
        "models": models, "jobs": jobs, "review_status": "unreviewed",
        "reused_completed_job_ids": [j["job_id"] for j in jobs if j["result_reused"]],
        "protocol_context": {
            "recovery_phase": proof.get("recovery_phase"),
            "max_output_tokens": proof.get("max_output_tokens_all_models", 2000),
            "four_non_openai_models_use_chat_bridge_in_phase3": proof.get("recovery_phase", 0) >= 3,
            "gpt_models_use_native_responses": True,
            "strict_schema_contract": "same original JSON schema and strict=true; no silent JSON-only fallback",
            "comparison_limitations": [
                "Phase 3 uses Responses for GPT models and a Chat Completions compatibility bridge for Gemini/Claude; wire protocol is a comparison condition.",
                "All continued model calls cap output at 2000 tokens for the Elice non-streaming proxy; earlier failed reservations used the previous cap.",
                "The 2000 total output-token cap includes provider reasoning. Observed default reasoning can leave too little visible JSON and cause finish_reason=length; this is a limit/compatibility observation, not approved model-quality failure.",
                "Sonnet source text recommends other models when JSON response format is required, while its generic API section lists response_format and structured-output compatibility; this is a documentation contradiction, not proven support.",
                "Unreviewed draft metrics do not support an approved quality ranking or pass threshold.",
            ]},
        "quality_evaluation": "diagnostic_only", "approved_accuracy_denominator": 0,
        "raw_cache_counter_policy": "Available top-level cache_write_tokens is preserved and validated against raw, SDK and transport totals; original tariff bounds and guard debits remain immutable; no posthoc repricing performed.",
        "semantic_judge_calls": 0, "billing_history_lookup": "explicitly_skipped_by_user",
        "limitations": [
            "Prior 404/400 failures have missing SDK usage and unknown actual cost; their reservations are holds, not invoices.",
            "No unknown attempt is replaced by zero cost; a later successful retry cannot erase earlier missing usage.",
            "Provider tariff bounds, known subtotals, and approved budget exposure are separate from actual confirmed cost.",
            "Any result case attempt with missing input/output totals makes its lifetime case cost unknown.",
            "Parent and fresh local attempt IDs are qualified by immutable run origin before unioning.",
            "Missing result rows use only marked explicit/sequential identity inference; unidentified attempts remain visible.",
            "Pinned terminal cancellation observations do not create SDK rows, outputs, token counts, or actual costs. Request cancellation does not prove provider error or timeout cause.",
            "B draft gold is unreviewed; strict/acceptable agreement is not approved correctness. Main and legacy NA remain separate.",
            "A reports service technical success and existing automatic checks; no semantic judge was called.",
            "A successful latency uses service wall time. Failed A zero placeholders use the recorded SDK latency sum and mark the source. B latency sums recorded attempt latencies. No latency is invented for missing orphan rows.",
            "Raw finish reasons, reasoning-token subsets, visible text characters, and explicit schema incompatibility are diagnostic only; raw body/error text is not copied into analysis artifacts.",
            "Some provider usage contains a top-level cache_write_tokens measurement omitted by the live normalizer. It is preserved as a separately validated observation; original conservative tariff bounds/debits are not retroactively changed.",
            "Billing history, taxes, account adjustments, and account credits were not looked up.",
        ]}
    accounting = {"version": 1, "run_directory": str(directory), "parent_directory": str(parent_path),
        "ancestor_directories": report["ancestor_directories"],
        "cases": [{k: v for k, v in c.items() if not k.startswith("_")} for c in cases],
        "unidentified_transport_attempts": [e for e in events if e["linked_case_key"] is None],
        "transport_attempt_index": events, "reconciliation": report["reconciliation"]}
    return report, accounting


def cost_text(cost: dict) -> str:
    if cost["status"] == "not_executed":
        return "미실행"
    if cost["status"] == "confirmed":
        return "$" + cost["cost_usd"]
    if cost["status"] == "bounded":
        return "$" + cost["cost_lower_usd"] + "–$" + cost["cost_upper_usd"] + " (범위)"
    return "미확인 (확인 상한 부분합 $" + cost["known_tariff_upper_subtotal_usd"] + ")"


def short(value: Any) -> str:
    if value is None:
        return "미확인"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def waste_ratio_text(waste: dict) -> str:
    if waste.get("actual_cost_ratio") is not None:
        return f"{Decimal(waste['actual_cost_ratio']) * 100:.2f}%"
    lower, upper = waste.get("actual_cost_ratio_lower"), waste.get("actual_cost_ratio_upper")
    if lower is not None and upper is not None:
        return f"{Decimal(lower) * 100:.2f}%–{Decimal(upper) * 100:.2f}% (범위)"
    return "미확인"


def render_report(report: dict) -> str:
    lines = ["# Elice 6모델 실험: 이어서 실행한 결과", "",
        "동일 16개 dev 입력 × 6개 모델, 총 96개 모델·사례. 정답 검수 상태는 **unreviewed**이다.", "",
        f"캠페인 상태: **{report['run_state']}**. 원래 404 시도와 새 실행을 출처별 ID로 합산했다.",
        "GPT a-dev-0001에서 발생한 이전 404·400 시도의 사용량과 실제 비용은 계속 미확인이다. 재실행 성공 여부가 이 기록을 지우지 않는다.", "",
        f"원본 결과에 기록된 사례 행은 **{report['source_recorded_cases']}개**, 별도 터미널 실패 관찰은 **{report['terminal_failure_observations']}개**이다. "
        f"논리적으로 종료된 관찰은 {report['logical_terminal_cases']}개이며, 터미널 관찰에 SDK 행이나 출력을 만들어 넣지 않았다.", "",
        "| 모델 | 성공/기술실패/미실행 | B main 초안 일치 | B legacy 초안 일치 | 서비스 총점 MAE main/legacy | 기술실패율 | 지연 p50/p95 ms | 실제 비용·범위 | 사례당 비용 |",
        "|---|---|---|---|---|---|---|---|---|"]
    for model in report["models"]:
        statuses = model["case_statuses"]
        main, legacy = model["B_draft_diagnostic"]["main"], model["B_draft_diagnostic"]["legacy_na"]
        blocked = model["quality_evaluation_status"] == "not_evaluated_strict_schema_incompatible"
        agreement = lambda v: "미평가 (엄격 스키마 미지원)" if blocked else f"{v['strict_matches']}/{v['expected_pairs']} (비교 {v['compared_pairs']})"
        mae = "미평가" if blocked else f"{short(main['service_total_absolute_deviation_mean'])}/{short(legacy['service_total_absolute_deviation_mean'])}"
        technical_rate = "적용 불가 (호환성 거절)" if blocked else short(model["technical_failure_rate_executed"])
        average = model["average_cost_per_attempted_case"]
        avg_text = "$" + average["cost_usd"] if average["cost_usd"] is not None else (
            "$" + average["cost_lower_usd"] + "–$" + average["cost_upper_usd"] if average["cost_lower_usd"] is not None else "미확인")
        lines.append(f"| {model['model_id']} | {statuses.get('succeeded', 0)}/{model['technical_failures']}/{statuses.get('not_executed', 0)} | "
            f"{agreement(main)} | {agreement(legacy)} | {mae} | "
            f"{technical_rate} | {short(model['latency_ms']['p50'])}/{short(model['latency_ms']['p95'])} | {cost_text(model['cost'])} | {avg_text} |")
    lines += ["", "비용과 예산은 다음처럼 구분한다.", "",
        f"- 실제 총비용: **{cost_text(report['cost'])}**. 미확인 사례 {report['unknown_cost_cases']}개, 미확인 시도 {report['cost']['unknown_attempts']}개.",
        f"- 새 실행에서 사용량으로 확인한 요금 상한 부분합: **${report['known_fresh_transport_upper_debit_usd']}**.",
        f"- 이전 실행에서 확인한 요금 상한 부분합: **${report['known_inherited_transport_upper_debit_usd']}**. 완료된 결과를 재사용해도 다시 청구하거나 합산하지 않는다.",
        f"- 이전 미확인 시도의 별도 예산 보류액 합계: **${report['inherited_unknown_reservation_hold_usd']}**. 실제 청구액으로 합산하지 않았다.",
        f"- 이전 보류를 포함한 ledger 기준 차감액: **${report['known_lifetime_budget_exposure_usd']}**. 마지막 미정산 예약 **${report['additional_unpriced_fresh_reservation_subtotal_usd']}**는 이 값에 별도로 더한다.",
        f"- 모든 미확인 시도의 보류·예약 합계: **${report['all_unknown_reservations_usd']}**.",
        f"- 확인 요금 상한 **${report['known_transport_tariff_upper_subtotal_usd']}** + 모든 미확인 예약을 합친 보수적 예산 노출액: **${report['conservative_budget_exposure_including_all_unknown_reservations_usd']}**. **실제 청구액이 아니다.**",
        f"- 새로운 미정산 전송 시도: {report['additional_unpriced_fresh_attempts']}개. 사용량과 실제 비용은 여전히 미확인이다.", "",
        "| 모델 | 입력/출력 토큰 확인 부분합 | 입력/출력 누락 시도 | 인터뷰당 비용 | B 초안 strict 일치 1쌍당 비용 | 재시도·실패 실제 비용 비율 |", 
        "|---|---|---|---|---|---|"]
    for model in report["models"]:
        tokens = model["tokens"]
        interview = model["average_cost_per_attempted_interview"]
        match = model["cost_per_strict_B_draft_pair_match_diagnostic"]
        price = lambda c: "$" + c["cost_usd"] if c["cost_usd"] is not None else (
            "$" + c["cost_lower_usd"] + "–$" + c["cost_upper_usd"] if c["cost_lower_usd"] is not None else "미확인")
        lines.append(f"| {model['model_id']} | {tokens['input_known_subtotal']}/{tokens['output_known_subtotal']} | "
            f"{tokens['missing_input_attempts']}/{tokens['missing_output_attempts']} | {price(interview)} | {price(match)} | {waste_ratio_text(model['retry_or_failure_cost'])} |")
    lines += ["", "| 모델 | HTTP 오류 | HTTP 200 뒤 서비스 실패 | 출력 잘림 시도 | 요청 취소 | 확인 추론 토큰 부분합 | 확인 화면 출력 문자 부분합 | 명시적 스키마 요청 거절 |",
        "|---|---|---|---|---|---|---|---|"]
    for model in report["models"]:
        lines.append(f"| {model['model_id']} | {model['http_error_attempts']} | {model['http_success_but_service_failed_attempts']} | "
            f"{model['truncated_attempts']} | {model['request_cancelled_attempts']} | {model['reasoning_output_tokens_known_subtotal']} | {model['visible_output_characters_known_subtotal']} | "
            f"{model['explicit_schema_request_rejection_attempts']} |")
    lines.append("")
    for model in report["models"]:
        schema_errors = model["stop_finished_schema_validation_failed_attempts"]
        contract_errors = model["stop_finished_contract_validation_failed_attempts"]
        if schema_errors or contract_errors:
            lines.append(f"- {model['model_id']}: finish_reason=stop 이후 스키마 검증 실패 {schema_errors}회, 서비스 계약 검증 실패 {contract_errors}회. "
                f"출력 잘림 {model['truncated_attempts']}회와 구분했으며, 이 수치를 승인된 모델 품질로 해석하지 않는다.")
        omitted = model["available_nonzero_raw_write_counter_omitted_by_live_normalizer_attempts"]
        if omitted:
            lines.append(f"- {model['model_id']}: 원문 top-level cache_write_tokens를 SDK·전송 입력/출력 합계와 대조해 {omitted}회 확인했다 "
                f"(관측된 계수 부분합 {model['raw_top_cache_write_tokens_validated_known_subtotal']}토큰). 이 계수는 실시간 정규화에서 누락되었으나 원문 측정값을 보존했다. "
                "기존의 보수적 요금 범위와 예산 상한 차감은 그대로 두었으며 사후 재가격 계산은 하지 않았다.")
    lines += ["", "사례당 평균은 시도가 있는 모델·사례를 분모로, 인터뷰당 평균은 시도가 있는 B 면접과 B 비용만 사용한다. "
        "B strict 일치당 비용은 미검수 초안과 일치한 쌍에 대한 진단이며 승인된 정답 1건당 비용이 아니다.", "",
        "실패한 A의 service_latency_ms=0 초기값은 실제 0ms로 사용하지 않았다. 기록된 SDK 지연 합계로 대체하고 latency_source에 표시했다. "
        "성공 사례의 실제 0ms는 유지하며, 응답·SDK 행이 없는 취소 시도에는 지연을 추정해 넣지 않았다.", "",
        f"완료된 이전 결과를 재사용한 작업: {', '.join(report['reused_completed_job_ids']) or '없음'}. 원본 파일과 계획의 해시를 확인하고 SDK 시도는 원래 출처에서 한 번만 계산했다.", "",
        "B main과 legacy NA의 strict/acceptable 일치, 숫자 단계 MAE, NA 쌍 수·불일치, 원래 서비스 점수 편차는 analysis.json에 각각 있다. "
        "미실행 쌍도 계획 분모에서 사라지지 않는다. A는 기술적 서비스 성공과 기존 자동 검사를 보고하며 의미 Judge는 실행하지 않았다.", "",
        f"출처가 다른 전송 시도 {report['transport_attempts']}개를 중복 없이 연결했다. SDK 행이 없는 전송 {report['reconciliation']['transport_attempts_without_result_sdk_row']}개, "
        f"사례를 특정하지 못한 전송 {report['transport_unidentified_orphan_attempts']}개, 정합성 이슈 {report['reconciliation']['issue_count']}개이다.", "",
        "모든 96개 상태, 원래 404의 orphan 연결·추론 표시, 각 SDK 시도 사용량과 요금 범위는 case-accounting.json에 남겼다. "
        "캐시 세부 요금이 확정되지 않으면 범위를 유지한다. 합격 임계값은 만들지 않았다. 사용자 지시에 따라 청구 내역 조회는 생략했다.", ""]
    protocol = report["protocol_context"]
    lines += [f"출력 상한은 모델당 {protocol['max_output_tokens']} 토큰이다. "
        "3차 복구에서는 GPT 두 모델의 Responses 경로와 Gemini·Claude 네 모델의 Chat Completions 브리지 경로가 다르며, 같은 strict JSON Schema를 유지한다. "
        "이 경로 차이도 비교 조건이다.", "",
        "Sonnet 원문은 JSON 응답 형식이 필요하면 다른 모델을 권하면서, 일반 API 절에서는 response_format 및 구조화 출력 호환성을 안내한다. "
        "문서 내부 불일치를 기록했다. 미검수 정답 초안으로 모델 순위나 합격 기준을 만들지 않았다.", ""]
    if report["explicit_strict_schema_rejected_models"]:
        lines += [f"{', '.join(report['explicit_strict_schema_rejected_models'])}는 이 프록시에서 response_format 강제 스키마 요청을 지원하지 않는다는 명시적 HTTP 400 응답을 받았다. "
            "따라서 품질은 **미평가 (엄격 스키마 미지원)**이며 0% 정답률이나 모델 품질 실패율로 표시하지 않았다. "
            "실제 기술 이벤트인 interrupted 1건과 미실행 사례는 그대로 보존했다.", ""]
    if not report["stopped_for_budget_exhaustion"] and report["explicit_strict_schema_rejected_models"]:
        lines += [f"이번 중단은 $10 예산 소진 때문이 아니다. 모든 미확인 예약을 포함한 보수적 노출액은 "
            f"${report['conservative_budget_exposure_including_all_unknown_reservations_usd']}이고 한도와의 차이는 ${report['conservative_reservation_margin_usd']}이다. "
            "마지막 스키마 거절의 사용량·비용을 확인할 수 없어 보호 장치가 중단했다.", ""]
    lines += ["출력 2000토큰 상한에는 추론 토큰도 포함된다. 이번 설정의 기본 추론 동작이 토큰을 많이 쓰면 화면에 보이는 JSON이 짧아지고 "
        "finish_reason=length로 잘릴 수 있다. 이 경우는 해당 상한·호환성 조건에서의 기술 실패이며 모델의 승인된 품질 실패로 일반화하지 않는다. "
        "추론 토큰은 출력 토큰의 부분집합으로 표시하며 비용을 다시 더하지 않았다. HTTP 오류, HTTP 200 이후 서비스 실패, 잘림과 명시적 스키마 거절을 각각 구분했다.", ""]
    if report["terminal_case_observations"]:
        for observation in report["terminal_case_observations"]:
            lines += [f"{observation['model_id']} / {observation['case_id']}는 원래 계획의 다음 미기록 사례와 취소 이벤트를 해시로 고정한 "
                f"**interrupted** 관찰이다({observation['source_lifetime_attempt_id']}). HTTP 응답·사용량·실제 비용·출력이 없으며 재시도하지 않는다. "
                "원인은 request_cancelled로 표시하며 공급자 오류나 타임아웃으로 확정하지 않았다.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("newrun_directory", type=Path)
    parser.add_argument("output_directory", type=Path, nargs="?")
    parser.add_argument("--output-dir", type=Path, dest="output_dir")
    args = parser.parse_args(argv)
    if args.output_dir is not None and args.output_directory is not None:
        parser.error("use either positional output_directory or --output-dir")
    directory = args.newrun_directory.resolve()
    output = (args.output_dir or args.output_directory or directory).resolve()
    if output.exists() and not output.is_dir():
        raise SystemExit("analysis output path is not a directory")
    if any((output / name).exists() for name in OUTPUT_NAMES):
        raise SystemExit("refusing to overwrite existing continuation analysis artifacts")
    if output != directory and output.exists() and any(output.iterdir()):
        raise SystemExit("separate analysis output directory must be fresh or empty")
    report, accounting = analyze(directory)
    report["analysis_output_directory"] = str(output)
    accounting["analysis_output_directory"] = str(output)
    artifacts = {"analysis.json": json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        "case-accounting.json": json.dumps(accounting, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        "report.md": render_report(report)}
    output.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    print(json.dumps({"run_state": report["run_state"], "case_statuses": report["case_statuses"],
        "analysis_output_directory": str(output),
        "source_recorded_cases": report["source_recorded_cases"],
        "terminal_failure_observations": report["terminal_failure_observations"],
        "exact_cost_total_usd": report["exact_cost_total_usd"],
        "known_fresh_transport_upper_debit_usd": report["known_fresh_transport_upper_debit_usd"],
        "inherited_unknown_reservation_hold_usd": report["inherited_unknown_reservation_hold_usd"],
        "unknown_cost_cases": report["unknown_cost_cases"],
        "original_unknown_attempt_preserved": report["original_unknown_attempt_preserved"],
        "reconciliation_issue_count": report["reconciliation"]["issue_count"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
