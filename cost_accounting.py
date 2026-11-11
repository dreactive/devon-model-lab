"""Offline Decimal accounting and an unconnected per-HTTP-attempt budget seam.

No provider imports, transport, environment reads, or paid execution live here.
Canonical input includes cached tokens; output includes reasoning tokens.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
import re
import threading
from typing import Any, Callable, TypeVar
from urllib.parse import urlparse

import yaml

MILLION = Decimal(1_000_000)
RATE_KEYS = ("input_usd_per_million", "output_usd_per_million",
             "cached_input_usd_per_million", "reasoning_output_usd_per_million")
STATUS_KO = {"confirmed": "확인", "unconfirmed": "미확인", "not_executed": "미실행",
             "collected": "수집", "not_collected": "미수집"}


def _usd(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _amount(value: Any, *, decimal_only: bool = False) -> Decimal:
    if (decimal_only and type(value) is not Decimal) or type(value) not in (Decimal, int, str):
        raise ValueError("amount_invalid")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("amount_invalid") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError("amount_invalid")
    return amount


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _sum_amounts(values: list[Decimal]) -> Decimal:
    """Keep reservation comparisons exact even beyond Decimal's default precision."""
    if not values:
        return Decimal(0)
    with localcontext() as context:
        context.prec = max(28, max(value.adjusted() for value in values)
                           - min(value.as_tuple().exponent for value in values)
                           + len(str(len(values))) + 2)
        return sum(values, Decimal(0))


class _PricingLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _PricingLoader, node: yaml.Node) -> dict:
    result: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if type(key) not in (str, int) or key in result:
            raise ValueError("pricing_invalid")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_PricingLoader.add_constructor("tag:yaml.org,2002:map", _mapping)
_PricingLoader.add_constructor("tag:yaml.org,2002:float", lambda loader, node: Decimal(node.value))
# Treat an ISO date as source text, rather than silently changing its type.
_PricingLoader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: node.value)


def _price_record(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict:
        raise ValueError("pricing_invalid")
    def missing(value: Any) -> bool:
        return value is None or (type(value) is str and not value.strip())
    result = {key: None if missing(raw.get(key)) else _amount(raw[key]) for key in RATE_KEYS}
    for key in ("source_url", "checked_at", "price_version"):
        result[key] = None if missing(raw.get(key)) else raw[key]
    url = result["source_url"]
    if url is not None:
        if type(url) is not str or urlparse(url).scheme not in ("https", "http") or not urlparse(url).netloc:
            raise ValueError("pricing_source_invalid")
    checked = result["checked_at"]
    if checked is not None:
        if type(checked) is not str:
            raise ValueError("pricing_date_invalid")
        try:
            if len(checked) == 10:
                date.fromisoformat(checked)
            else:
                parsed = datetime.fromisoformat(checked.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError
        except ValueError:
            raise ValueError("pricing_date_invalid") from None
    if result["price_version"] is not None and type(result["price_version"]) is not str:
        raise ValueError("pricing_version_invalid")
    missing_fields = [key for key in (*RATE_KEYS[:2], "source_url", "checked_at", "price_version") if result[key] is None]
    status = "not_collected" if missing_fields else "collected"
    result.update(status=status, status_ko=STATUS_KO[status], missing_fields=missing_fields)
    return result


def load_pricing(path: str | Path) -> dict[str, Any]:
    """Read user-entered rates, preserving Decimal values and validating provenance."""
    try:
        raw = yaml.load(Path(path).read_text(encoding="utf-8-sig"), Loader=_PricingLoader)
        if (type(raw) is not dict or type(raw.get("version")) is not int or raw["version"] != 1
                or raw.get("currency") != "USD" or raw.get("unit") not in
                (1_000_000, "1Mtokens", "1M_tokens", "per_1m_tokens") or type(raw.get("models")) is not dict):
            raise ValueError("pricing_invalid")
        models = {}
        for model, record in raw["models"].items():
            if type(model) is not str or not model.strip():
                raise ValueError("pricing_model_invalid")
            models[model] = _price_record(record)
        return {"version": 1, "currency": "USD", "unit": 1_000_000, "models": models}
    except (OSError, UnicodeError, yaml.YAMLError, InvalidOperation, TypeError, RecursionError):
        raise ValueError("pricing_invalid") from None


def _lookup(pricing: dict, model: Any) -> dict | None:
    raw = pricing.get("models", {}).get(model) if type(model) is str and model.strip() else None
    return _price_record(raw) if raw is not None else None


def _attempt_cost(attempt: dict, pricing: dict) -> dict:
    model = attempt.get("model")
    rates = _lookup(pricing, model)
    limitations: list[str] = []
    missing_tokens = any(not _count(attempt.get(key)) for key in ("input_tokens", "output_tokens"))
    missing_price = rates is None or rates["status"] != "collected"
    if missing_tokens:
        limitations.append("input_or_output_tokens_missing_or_invalid")
    if missing_price:
        limitations.append("model_price_not_collected" if model else "attempt_model_missing")
    total = Decimal(0)
    for canonical, detail, normal_rate, special_rate in (
        ("input_tokens", "cached_input_tokens", RATE_KEYS[0], RATE_KEYS[2]),
        ("output_tokens", "reasoning_output_tokens", RATE_KEYS[1], RATE_KEYS[3]),
    ):
        count, subset = attempt.get(canonical), attempt.get(detail)
        if detail in attempt and (not _count(subset) or not _count(count) or subset > count):
            limitations.append(f"{detail}_invalid_subset")
            continue
        if rates is None or rates[normal_rate] is None or not _count(count):
            continue
        if rates[special_rate] is not None and rates[special_rate] != rates[normal_rate] and detail not in attempt:
            limitations.append(f"{detail}_breakdown_unavailable")
            continue
        if subset and rates[special_rate] is None:
            limitations.append(f"{detail}_price_not_collected")
            missing_price = True
            continue
        total += (Decimal(count - (subset or 0)) * rates[normal_rate]
                  + Decimal(subset or 0) * (rates[special_rate] if rates[special_rate] is not None else rates[normal_rate])) / MILLION
    return {"cost_usd": None if limitations else total, "limitations": limitations,
            "missing_tokens": missing_tokens, "missing_price": missing_price, "model": model}


def _bucket(entries: list[dict], *, ambiguous: bool = False) -> dict:
    known = sum((entry["cost_usd"] for entry in entries if entry["cost_usd"] is not None), Decimal(0))
    unknown = sum(entry["cost_usd"] is None for entry in entries)
    status = "unconfirmed" if ambiguous else "not_executed" if not entries else "unconfirmed" if unknown else "confirmed"
    tokens = {}
    for key in ("input_tokens", "output_tokens"):
        values = [entry["attempt"].get(key) for entry in entries]
        missing = sum(not _count(value) for value in values)
        subtotal = sum(value for value in values if _count(value))
        tokens[key] = {"known_subtotal": subtotal, "total": subtotal if entries and not missing and not ambiguous else None,
                       "missing_attempts": missing}
    return {"status": status, "status_ko": STATUS_KO[status], "total_usd": _usd(known) if status == "confirmed" else None,
            "known_subtotal_usd": _usd(known), "attempts": len(entries), "unknown_attempts": unknown,
            "missing_token_attempts": sum(entry["missing_tokens"] for entry in entries),
            "missing_price_attempts": sum(entry["missing_price"] for entry in entries), "tokens": tokens}


def _ratio(amount: str | None, divisor: int | Decimal) -> str | None:
    return _usd(Decimal(amount) / divisor) if amount is not None and divisor else None


def _percentile(values: list[int | float], fraction: Decimal) -> int | float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = Decimal(len(values) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    result = Decimal(str(ordered[lower])) + (Decimal(str(ordered[upper])) - Decimal(str(ordered[lower]))) * (index - lower)
    return int(result) if result == result.to_integral() else float(result)


def _latency_summary(values: list[int | float]) -> dict:
    return {"p50": _percentile(values, Decimal("0.5")), "p95": _percentile(values, Decimal("0.95")),
            "measured_cases": len(values)}


def _measured_latency(value: Any) -> bool:
    return type(value) in (int, float) and value >= 0 and Decimal(str(value)).is_finite()


def _approved_items(row: dict) -> int:
    metrics = row.get("metrics", {})
    if type(metrics) is not dict:
        return 0
    if _count(metrics.get("confirmed_correct_items")):
        return metrics["confirmed_correct_items"]
    if (_count(metrics.get("exact_matches")) and _count(metrics.get("denominator"))
            and metrics["exact_matches"] <= metrics["denominator"]):
        return metrics["exact_matches"]
    return 0


def _reconcile_judges(result: dict) -> tuple[list[dict], int, int]:
    """Prefer complete final audit; recover nested checkpoint attempts by identity."""
    top = result.get("judge_audit", [])
    if type(top) is not list or any(type(row) is not dict for row in top):
        raise ValueError("judge_audit_invalid")
    audit_rows = list(top)
    fields = ("attempt", "provider", "model", "prompt_version", "schema_version", "latency_ms",
              "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens",
              "error_stage", "error_code", "response_id")
    def identity(attempt: dict) -> tuple | None:
        response_id = attempt.get("response_id")
        if type(response_id) is not str or not response_id.strip():
            return None
        values = tuple(attempt.get(key) for key in fields)
        return values if all(type(value) in (str, int, float, bool, type(None)) for value in values) else None
    available: dict[tuple, int] = {}
    for audit in top:
        attempts = audit.get("attempts", [])
        if type(attempts) is not list or any(type(attempt) is not dict for attempt in attempts):
            raise ValueError("attempts_invalid")
        for attempt in attempts:
            key = identity(attempt)
            if key is not None:
                available[key] = available.get(key, 0) + 1
    metadata = result.get("metadata", {})
    if type(metadata) is not dict:
        raise ValueError("metadata_invalid")
    grader = metadata.get("grader", {})
    configured = ((type(grader) is dict and grader.get("kind") == "bounded_llm_judge")
                  or (_count(metadata.get("max_judge_attempts")) and metadata["max_judge_attempts"] > 0))
    incomplete = int(configured and ("judge_audit" not in result or result.get("run_state") not in (None, "completed")))
    reconciled = 0
    cases = result.get("cases", [])
    if type(cases) is not list or any(type(row) is not dict for row in cases):
        raise ValueError("results_invalid")
    for row in cases:
        for name in ("judge", "diagnostic_judge"):
            nested = row.get(name)
            if nested is None:
                continue
            if type(nested) is not dict:
                raise ValueError("nested_judge_invalid")
            attempts = nested.get("attempts")
            if attempts is None or attempts == []:
                incomplete += 1
                continue
            if type(attempts) is not list or any(type(attempt) is not dict for attempt in attempts):
                raise ValueError("attempts_invalid")
            unmatched = []
            for attempt in attempts:
                key = identity(attempt)
                if key is not None and available.get(key, 0):
                    available[key] -= 1
                    reconciled += 1
                else:
                    unmatched.append(attempt)
                    # Without a response identity, a final audit and nested log
                    # may mirror the same bill. Retain both and expose uncertainty.
                    if key is None and top:
                        incomplete += 1
            if unmatched:
                audit_rows.append({"case_id": row.get("case_id", row.get("case")), "attempts": unmatched,
                                   "failure": nested.get("failure"), "audit_source": name})
    return audit_rows, incomplete, reconciled


def _waste_summary(entries: list[dict], total: dict) -> dict:
    retry = _bucket([entry for entry in entries if entry["is_retry"]])
    failed_case = _bucket([entry for entry in entries if entry["failed_case"]])
    failure = _bucket([entry for entry in entries if entry["failed_case"] or entry["failed_attempt"]])
    waste = _bucket([entry for entry in entries if entry["is_retry"] or entry["failed_case"] or entry["failed_attempt"]])
    def cost(bucket: dict) -> str | None:
        return "0" if entries and bucket["attempts"] == 0 else bucket["total_usd"]
    return {"retry_cost_usd": cost(retry), "retry_known_subtotal_usd": retry["known_subtotal_usd"],
            "failed_case_cost_usd": cost(failed_case), "failed_case_known_subtotal_usd": failed_case["known_subtotal_usd"],
            "failure_cost_usd": cost(failure), "failure_known_subtotal_usd": failure["known_subtotal_usd"],
            "retry_or_failure_cost_usd": cost(waste), "retry_or_failure_known_subtotal_usd": waste["known_subtotal_usd"],
            "retry_or_failure_share": _ratio(cost(waste), Decimal(total["total_usd"])) if total["total_usd"] else None}


def _model_summary(entries: list[dict], contexts: list[dict], *, ambiguous: bool) -> dict:
    total = _bucket(entries, ambiguous=ambiguous)
    service = _bucket([entry for entry in entries if entry["channel"] == "service"])
    judge = _bucket([entry for entry in entries if entry["channel"] == "judge"])
    model = entries[0]["model"]
    relevant = [item for item in contexts if any(entry["model"] == model for entry in item["entries"])]
    interview_count = len({item["interview"] for item in relevant})
    measured = []
    deviations = []
    for item in relevant:
        selected = [entry for entry in item["entries"] if entry["model"] == model]
        if len(selected) == len(item["entries"]) and _measured_latency(item["latency"]):
            measured.append(item["latency"])
        elif selected and all(_measured_latency(entry["attempt"].get("latency_ms")) for entry in selected):
            measured.append(sum(entry["attempt"]["latency_ms"] for entry in selected))
        metrics = item["row"].get("metrics", {})
        if item["approved"] and type(metrics) is dict and _measured_latency(metrics.get("mean_absolute_deviation")):
            deviations.append(Decimal(str(metrics["mean_absolute_deviation"])))
    correct_cases = sum(item["correct_case"] for item in relevant)
    correct_items = sum(item["correct_items"] for item in relevant)
    experiments = {entry["experiment"] for entry in entries}
    a_total = _bucket([entry for entry in entries if entry["experiment"] == "A"], ambiguous=ambiguous)["total_usd"]
    b_total = _bucket([entry for entry in entries if entry["experiment"] == "B"], ambiguous=ambiguous)["total_usd"]
    return {**total, "service": service, "judge": judge,
            "counts": {"executed_cases": len(relevant), "interviews": interview_count,
                       "service_failures": sum(item["failed"] for item in relevant),
                       "failed_attempts": sum(entry["failed_attempt"] for entry in entries),
                       **{key: total[key] for key in ("attempts", "unknown_attempts", "missing_token_attempts", "missing_price_attempts")}},
            "averages": {"service_per_case_usd": _ratio(service["total_usd"], len(relevant)),
                         "service_per_interview_usd": _ratio(service["total_usd"], interview_count),
                         "all_in_per_case_usd": _ratio(total["total_usd"], len(relevant)),
                         "all_in_per_interview_usd": _ratio(total["total_usd"], interview_count)},
            "efficiency": {"confirmed_correct_cases": correct_cases, "confirmed_correct_items": correct_items,
                           "cost_per_confirmed_correct_case_usd": _ratio(a_total, correct_cases),
                           "cost_per_confirmed_correct_item_usd": _ratio(b_total, correct_items),
                           "cost_per_confirmed_correct_usd": _ratio(a_total, correct_cases) if experiments == {"A"} else
                                _ratio(b_total, correct_items) if experiments == {"B"} else None},
            "latency_ms": _latency_summary(measured), "waste": _waste_summary(entries, total),
            "quality": {"service_score_deviation": _usd(sum(deviations, Decimal(0)) / len(deviations)) if deviations else None},
            "score_deviation": _usd(sum(deviations, Decimal(0)) / len(deviations)) if deviations else None,
            "score_deviation_basis": "approved_explicit_case_mean_absolute_deviation" if deviations else "not_collected"}


def summarize_results(results: list[dict], pricing: dict) -> dict[str, Any]:
    """Include service and independent judge attempts; unknowns never become zero."""
    if type(results) is not list or any(type(result) is not dict for result in results):
        raise ValueError("results_invalid")
    with localcontext() as context:
        context.prec = 80
        return _summarize_results(results, pricing)


def _summarize_results(results: list[dict], pricing: dict) -> dict:
    entries: list[dict] = []
    case_reports: list[dict] = []
    audit_reports: list[dict] = []
    latencies: list[int | float] = []
    service_failures = preflight_failures = 0
    correct_cases = correct_items = executed_cases = 0
    interview_ids: set[tuple[int, str]] = set()
    experiment_entries: dict[str, list[dict]] = {"A": [], "B": []}
    # response_id alone cannot safely identify a charge. Flag cross-log repeats;
    # retain every logged attempt and make the combined total unresolved.
    response_logs: dict[tuple[str, str, str], set[tuple[int, str]]] = {}
    duplicate_keys: set[tuple[str, str, str]] = set()
    contexts: list[dict] = []
    incomplete_audits = reconciled_judge_attempts = 0
    for run_no, result in enumerate(results):
        experiment = result.get("experiment", "A")
        if type(experiment) is not str:
            raise ValueError("experiment_invalid")
        audits, incomplete, reconciled = _reconcile_judges(result)
        incomplete_audits += incomplete
        reconciled_judge_attempts += reconciled
        for channel, rows, destination in (("service", result.get("cases", []), case_reports), ("judge", audits, audit_reports)):
            if type(rows) is not list or any(type(row) is not dict for row in rows):
                raise ValueError("results_invalid")
            for row_no, row in enumerate(rows):
                attempts = row.get("attempts", [])
                if type(attempts) is not list or any(type(attempt) is not dict for attempt in attempts):
                    raise ValueError("attempts_invalid")
                row_entries: list[dict] = []
                seen_tasks: set[tuple[Any, ...]] = set()
                failed = row.get("status") == "failed" or bool(row.get("failure"))
                for attempt in attempts:
                    task = tuple(attempt.get(key) for key in ("provider", "model", "prompt_version", "schema_version"))
                    valid_task = all(type(value) is str and value.strip() for value in task)
                    is_retry = attempt.get("is_retry") is True or (valid_task and task in seen_tasks)
                    if valid_task:
                        seen_tasks.add(task)
                    entry = {**_attempt_cost(attempt, pricing), "attempt": attempt, "channel": channel,
                             "is_retry": is_retry, "failed_case": failed,
                             "failed_attempt": bool(attempt.get("error_stage") or attempt.get("error_code")),
                             "experiment": experiment}
                    row_entries.append(entry)
                    entries.append(entry)
                    if experiment in experiment_entries:
                        experiment_entries[experiment].append(entry)
                    response_id = attempt.get("response_id")
                    if type(response_id) is str and response_id.strip():
                        key = (str(attempt.get("provider")), str(attempt.get("model")), response_id)
                        logs = response_logs.setdefault(key, set())
                        log = (run_no, channel)
                        if logs and log not in logs:
                            duplicate_keys.add(key)
                        logs.add(log)
                bucket = _bucket(row_entries)
                destination.append({"run_index": run_no, "case_id": row.get("case_id", row.get("case")),
                                    "source_status": row.get("status"), **bucket,
                                    "limitations": sorted({reason for entry in row_entries for reason in entry["limitations"]})})
                if channel != "service":
                    continue
                if not attempts:
                    preflight_failures += int(failed)
                    continue
                service_failures += int(failed)
                executed_cases += 1
                interview = (run_no, str(row.get("interview_id", row.get("case_id", row.get("case", row_no)))))
                interview_ids.add(interview)
                latency = row.get("service_latency_ms", row.get("latency_ms"))
                if _measured_latency(latency):
                    latencies.append(latency)
                approved = row.get("review_status") == "approved"
                correct_case = experiment == "A" and approved and row.get("quality") in ("accept", "quality_accept") and not failed
                items = _approved_items(row) if experiment == "B" and approved and not failed else 0
                correct_cases += int(correct_case)
                correct_items += items
                contexts.append({"entries": row_entries, "interview": interview, "latency": latency,
                                 "approved": approved, "correct_case": correct_case, "correct_items": items,
                                 "failed": failed, "row": row})
    total = _bucket(entries, ambiguous=bool(duplicate_keys) or bool(incomplete_audits))
    service = _bucket([entry for entry in entries if entry["channel"] == "service"])
    judge = _bucket([entry for entry in entries if entry["channel"] == "judge"], ambiguous=bool(duplicate_keys) or bool(incomplete_audits))
    models = {}
    for model in sorted({entry["model"] for entry in entries if type(entry["model"]) is str}):
        models[model] = _model_summary([entry for entry in entries if entry["model"] == model], contexts,
                                      ambiguous=any(key[1] == model for key in duplicate_keys) or bool(incomplete_audits))
    if any(type(entry["model"]) is not str for entry in entries):
        models["<missing-model>"] = _model_summary([entry for entry in entries if type(entry["model"]) is not str], contexts,
                                                   ambiguous=bool(incomplete_audits))
    a_total = _bucket(experiment_entries["A"], ambiguous=bool(duplicate_keys) or bool(incomplete_audits))["total_usd"]
    b_total = _bucket(experiment_entries["B"], ambiguous=bool(duplicate_keys) or bool(incomplete_audits))["total_usd"]
    return {"version": 1, "currency": "USD", "token_unit": 1_000_000,
            **{key: total[key] for key in ("status", "status_ko", "total_usd", "known_subtotal_usd", "tokens")},
            "counts": {"cases": len(case_reports), "executed_cases": executed_cases,
                       "not_executed_cases": len(case_reports) - executed_cases, "interviews": len(interview_ids),
                       "unknown_cases": sum(row["status"] == "unconfirmed" for row in case_reports),
                       "missing_token_cases": sum(row["missing_token_attempts"] > 0 for row in case_reports),
                       "missing_price_cases": sum(row["missing_price_attempts"] > 0 for row in case_reports),
                       "failed_attempts": sum(entry["failed_attempt"] for entry in entries),
                       "service_failures": service_failures, "preflight_failures": preflight_failures,
                       "ambiguous_cross_log_duplicates": len(duplicate_keys), "incomplete_judge_audits": incomplete_audits,
                       "reconciled_nested_judge_attempts": reconciled_judge_attempts,
                       **{key: total[key] for key in ("attempts", "unknown_attempts", "missing_token_attempts", "missing_price_attempts")}},
            "service": service, "judge": judge, "models": models, "cases": case_reports, "judge_audit": audit_reports,
            "averages": {"service_per_case_usd": _ratio(service["total_usd"], executed_cases),
                         "service_per_interview_usd": _ratio(service["total_usd"], len(interview_ids)),
                         "judge_overhead_per_case_usd": _ratio("0" if judge["status"] == "not_executed" else judge["total_usd"], executed_cases),
                         "all_in_per_case_usd": _ratio(total["total_usd"], executed_cases),
                         "all_in_per_interview_usd": _ratio(total["total_usd"], len(interview_ids))},
            "efficiency": {"confirmed_correct_cases": correct_cases, "confirmed_correct_items": correct_items,
                           "cost_per_confirmed_correct_case_usd": _ratio(a_total, correct_cases),
                           "cost_per_confirmed_correct_item_usd": _ratio(b_total, correct_items),
                           "cost_per_confirmed_correct_usd": _ratio(a_total, correct_cases) if not experiment_entries["B"] else
                                _ratio(b_total, correct_items) if not experiment_entries["A"] else None,
                           "quality_status": "collected" if correct_cases or correct_items else "not_collected"},
            "waste": _waste_summary(entries, total), "latency_ms": _latency_summary(latencies),
            "limitations": (["cross_log_response_id_ambiguity_all_attempts_retained"] if duplicate_keys else [])
                            + (["judge_audit_incomplete"] if incomplete_audits else [])}


def estimate_cost(model: str, *, input_tokens_lower: int, input_tokens_upper: int,
                  output_tokens_upper: int, calls_lower: int, calls_upper: int, pricing: dict) -> dict:
    """Planning range only; a caller's input heuristic is not a billing estimate guarantee."""
    values = (input_tokens_lower, input_tokens_upper, output_tokens_upper, calls_lower, calls_upper)
    if any(not _count(value) for value in values) or input_tokens_lower > input_tokens_upper or calls_lower > calls_upper:
        raise ValueError("estimate_range_invalid")
    rates = _lookup(pricing, model)
    limitations: list[str] = []
    lower = upper = None
    if rates is None or rates["status"] != "collected":
        limitations.append("model_price_not_collected")
    else:
        distinct = any(rates[special] is not None and rates[special] != rates[normal]
                       for normal, special in ((RATE_KEYS[0], RATE_KEYS[2]), (RATE_KEYS[1], RATE_KEYS[3])))
        with localcontext() as context:
            context.prec = 80
            input_max = max(rate for key in (RATE_KEYS[0], RATE_KEYS[2]) if (rate := rates[key]) is not None)
            output_max = max(rate for key in (RATE_KEYS[1], RATE_KEYS[3]) if (rate := rates[key]) is not None)
            upper = (Decimal(input_tokens_upper) * input_max + Decimal(output_tokens_upper) * output_max) * calls_upper / MILLION
            if distinct:
                limitations.append("cached_or_reasoning_breakdown_unavailable_upper_uses_max_rates")
            else:
                lower = Decimal(input_tokens_lower) * rates[RATE_KEYS[0]] * calls_lower / MILLION
    status = "unconfirmed" if limitations else "estimated"
    return {"model": model, "currency": "USD", "status": status,
            "expected_lower_usd": _usd(lower), "expected_upper_usd": _usd(upper),
            "input_tokens_lower": input_tokens_lower, "input_tokens_upper": input_tokens_upper,
            "output_tokens_lower": 0, "output_tokens_upper": output_tokens_upper,
            "calls_lower": calls_lower, "calls_upper": calls_upper, "limitations": limitations,
            "billing_guarantee": False}


class BudgetRejected(RuntimeError):
    """An attempt must not start after this fixed-code rejection."""


class CostBudget:
    """Thread-safe reservations for an approved transport, never a billing cap guarantee.

    Call reserve immediately before EACH actual HTTP attempt, including retries.
    The caller owns a conservative known upper bound and its approval provenance.
    """
    def __init__(self, amount_usd: Decimal, max_attempts: int, *, approval_id: str | None = None,
                 approved: bool = False) -> None:
        amount = _amount(amount_usd, decimal_only=True)
        if amount <= 0 or not _count(max_attempts) or max_attempts < 1:
            raise ValueError("budget_invalid")
        if not ((type(approval_id) is str and approval_id.strip()) or approved is True):
            raise ValueError("budget_approval_required")
        self.amount_usd, self.max_attempts = amount, max_attempts
        self.approval_id = approval_id.strip() if type(approval_id) is str else None
        self._lock = threading.Lock()
        self._reservations: dict[str, Decimal] = {}
        self._spent = Decimal(0)
        self._attempts = self._unknown = 0
        self._halt_reason: str | None = None

    def reserve(self, upper_usd: Decimal) -> str:
        """Atomically reserve dollars and one attempt before any operation begins."""
        upper = _amount(upper_usd, decimal_only=True)
        with self._lock:
            if self._halt_reason:
                raise BudgetRejected(self._halt_reason)
            if self._attempts >= self.max_attempts:
                raise BudgetRejected("attempt_cap_reached")
            if _sum_amounts([self._spent, *self._reservations.values(), upper]) > self.amount_usd:
                raise BudgetRejected("monetary_cap_insufficient")
            self._attempts += 1
            ticket = f"attempt-{self._attempts}"
            self._reservations[ticket] = upper
            return ticket

    def settle(self, reservation_id: str, actual_usd: Decimal | None) -> None:
        """Unknown billed cost halts future starts; known cost can exceed the estimate."""
        actual = None if actual_usd is None else _amount(actual_usd, decimal_only=True)
        with self._lock:
            if reservation_id not in self._reservations:
                raise ValueError("reservation_invalid")
            self._reservations.pop(reservation_id)
            if actual is None:
                self._unknown += 1
                self._halt_reason = "actual_cost_unconfirmed"
            else:
                self._spent = _sum_amounts([self._spent, actual])
                if _sum_amounts([self._spent, *self._reservations.values()]) > self.amount_usd:
                    self._halt_reason = "actual_cost_cap_exceeded"

    def halt(self, reason: str) -> None:
        """Stop all future reservations without changing recorded spend."""
        if type(reason) is not str or re.fullmatch(r"[a-z0-9_]{1,128}", reason) is None:
            raise ValueError("halt_reason_invalid")
        with self._lock:
            self._halt_reason = self._halt_reason or reason

    def to_dict(self) -> dict:
        with self._lock:
            reserved = _sum_amounts(list(self._reservations.values()))
            remaining = _sum_amounts([self.amount_usd, self._spent.copy_negate(), reserved.copy_negate()])
            return {"amount_usd": _usd(self.amount_usd), "max_attempts": self.max_attempts,
                    "approval_id": self.approval_id, "attempts_started": self._attempts,
                    "spent_usd": _usd(self._spent), "reserved_usd": _usd(reserved),
                    "remaining_usd": None if self._unknown else _usd(max(Decimal(0), remaining)),
                    "unknown_attempts": self._unknown, "in_flight_attempts": len(self._reservations),
                    "halted": self._halt_reason is not None, "halt_reason": self._halt_reason,
                    "transport_integration": "requires_transport_binding"}


T = TypeVar("T")


def run_guarded_attempt(budget: CostBudget, upper_usd: Decimal, operation: Callable[[], T],
                        cost_of_result: Callable[[T], Decimal | None]) -> T:
    """Simulation/integration seam; operation must represent exactly one HTTP attempt."""
    ticket = budget.reserve(upper_usd)
    try:
        result = operation()
        actual = cost_of_result(result)
        # Validate inside the guarded region so a broken extractor cannot release
        # an attempt without recording that billed usage is unknown.
        if actual is not None:
            actual = _amount(actual, decimal_only=True)
    except BaseException:
        budget.settle(ticket, None)
        raise
    budget.settle(ticket, actual)
    return result
