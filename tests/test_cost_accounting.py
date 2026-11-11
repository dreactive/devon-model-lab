"""Offline, hand-calculated accounting and per-attempt budget behavior."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))


def attempt(**changes):
    return {"attempt": 1, "provider": "offline", "model": "test-model",
            "prompt_version": "8", "schema_version": "plan-1", "latency_ms": 10,
            "input_tokens": 1000, "output_tokens": 100,
            "error_stage": None, "error_code": None, "response_id": None, **changes}


def price(**changes):
    return {"input_usd_per_million": "1.25", "output_usd_per_million": "5",
            "cached_input_usd_per_million": None, "reasoning_output_usd_per_million": None,
            "source_url": "https://example.test/prices", "checked_at": "2026-11-10",
            "price_version": "test-1", **changes}


class AccountingTests(unittest.TestCase):
    def module(self):
        self.assertTrue((LAB / "cost_accounting.py").is_file(), "cost accounting implementation missing")
        return importlib.import_module("cost_accounting")

    def pricing(self, record=None):
        module = self.module()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as temporary:
            path = Path(temporary) / "prices.yaml"
            path.write_text(json.dumps({"version": 1, "currency": "USD", "unit": "1Mtokens",
                                         "models": {"test-model": record or price()}}), encoding="utf-8")
            return module.load_pricing(path)

    def summarize(self, cases, **run):
        return self.module().summarize_results([{"experiment": "A", "cases": cases, **run}], self.pricing())

    def test_decimal_all_attempts_and_distinct_director_review_are_billed(self):
        row = {"case_id": "a", "status": "succeeded", "review_status": "approved", "quality": "accept",
               "attempts": [attempt(), attempt(attempt=2, schema_version="review-1")], "latency_ms": 20}
        report = self.summarize([row])
        self.assertEqual(report["total_usd"], "0.0035")
        self.assertEqual(report["waste"]["retry_cost_usd"], "0")
        self.assertEqual(report["efficiency"]["confirmed_correct_cases"], 1)
        json.dumps(report, allow_nan=False)

    def test_missing_usage_keeps_total_unknown_and_visible_case(self):
        report = self.summarize([{"case_id": "ok", "status": "failed", "attempts": [attempt()]},
                                 {"case_id": "unknown", "status": "failed", "attempts": [attempt(input_tokens=None)]}])
        self.assertIsNone(report["total_usd"])
        self.assertEqual(report["known_subtotal_usd"], "0.00175")
        self.assertEqual(report["counts"]["missing_token_attempts"], 1)
        self.assertEqual(report["cases"][1]["status"], "unconfirmed")
        self.assertIsNone(report["tokens"]["input_tokens"]["total"])
        self.assertEqual(report["tokens"]["input_tokens"]["known_subtotal"], 1000)

    def test_retry_failed_case_union_does_not_double_count(self):
        report = self.summarize([{"case_id": "failed", "status": "failed",
                                 "attempts": [attempt(error_code="timeout"), attempt(attempt=2)]}])
        self.assertEqual(report["waste"]["retry_cost_usd"], "0.00175")
        self.assertEqual(report["waste"]["failed_case_cost_usd"], "0.0035")
        self.assertEqual(report["waste"]["retry_or_failure_cost_usd"], "0.0035")
        self.assertEqual(report["waste"]["retry_or_failure_share"], "1")
        self.assertEqual(report["counts"]["service_failures"], 1)

    def test_failed_first_attempt_is_waste_even_when_case_eventually_succeeds(self):
        report = self.summarize([{"case_id": "recovered", "status": "succeeded",
                                 "attempts": [attempt(error_stage="timeout", error_code="timeout"), attempt(attempt=2)]}])
        self.assertEqual(report["waste"]["failure_cost_usd"], "0.00175")
        self.assertEqual(report["waste"]["failed_case_cost_usd"], "0")
        self.assertEqual(report["waste"]["retry_or_failure_cost_usd"], "0.0035")
        self.assertEqual(report["counts"]["failed_attempts"], 1)

    def test_judge_controls_are_billed_separately_from_case_average(self):
        report = self.summarize([{"case_id": "a", "status": "succeeded", "attempts": [attempt()]}],
                                judge_audit=[{"case_id": "control-not-in-cases", "attempts": [attempt()]}])
        self.assertEqual(report["total_usd"], "0.0035")
        self.assertEqual(report["judge"]["total_usd"], "0.00175")
        self.assertEqual(report["averages"]["service_per_case_usd"], "0.00175")
        self.assertEqual(report["averages"]["all_in_per_case_usd"], "0.0035")

    def test_no_attempts_are_not_free_execution_or_latency_measurement(self):
        report = self.summarize([{"case_id": "dry", "status": "validated_only", "latency_ms": 0}])
        self.assertEqual(report["status"], "not_executed")
        self.assertIsNone(report["total_usd"])
        self.assertEqual(report["cases"][0]["status"], "not_executed")
        self.assertIsNone(report["latency_ms"]["p50"])

    def test_exact_model_and_invalid_tokens_do_not_guess_or_accept_bool(self):
        for changes in ({"model": "different"}, {"model": None}, {"input_tokens": True}, {"output_tokens": -1}):
            with self.subTest(changes=changes):
                report = self.summarize([{"case_id": "a", "attempts": [attempt(**changes)]}])
                self.assertIsNone(report["total_usd"])
                self.assertEqual(report["counts"]["unknown_attempts"], 1)

    def test_cached_and_reasoning_are_subsets_not_added_twice(self):
        pricing = self.pricing(price(cached_input_usd_per_million="0.25", reasoning_output_usd_per_million="10"))
        row = {"case_id": "a", "attempts": [attempt(cached_input_tokens=400, reasoning_output_tokens=20)]}
        report = self.module().summarize_results([{"cases": [row]}], pricing)
        self.assertEqual(report["total_usd"], "0.00145")

    def test_distinct_rates_without_breakdown_and_invalid_subsets_stay_unknown(self):
        pricing = self.pricing(price(cached_input_usd_per_million="0.25"))
        for changes in ({}, {"cached_input_tokens": 1001}, {"cached_input_tokens": True}):
            with self.subTest(changes=changes):
                report = self.module().summarize_results([{"cases": [{"attempts": [attempt(**changes)]}]}], pricing)
                self.assertIsNone(report["total_usd"])
                self.assertTrue(report["cases"][0]["limitations"])

    def test_null_prices_are_not_collected_and_source_metadata_is_required(self):
        pricing = self.pricing(price(input_usd_per_million=None, output_usd_per_million=None,
                                     source_url=None, checked_at=None, price_version=None))
        self.assertEqual(pricing["models"]["test-model"]["status"], "not_collected")
        report = self.module().summarize_results([{"cases": [{"attempts": [attempt()]}]}], pricing)
        self.assertEqual(report["counts"]["missing_price_attempts"], 1)
        for changes in ({"source_url": "local-file"}, {"checked_at": "2026-02-30"},
                        {"input_usd_per_million": -1}, {"output_usd_per_million": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.pricing(price(**changes))

    def test_partial_blank_prices_or_provenance_only_leave_that_model_uncollected(self):
        module = self.module()
        for changes in ({"input_usd_per_million": " "}, {"source_url": None}, {"checked_at": ""}, {"price_version": " "}):
            with self.subTest(changes=changes):
                partial = self.pricing(price(**changes))
                self.assertEqual(partial["models"]["test-model"]["status"], "not_collected")
                self.assertTrue(partial["models"]["test-model"]["missing_fields"])
                partial["models"]["good-model"] = self.pricing()["models"]["test-model"]
                report = module.summarize_results([{"cases": [
                    {"attempts": [attempt()]}, {"attempts": [attempt(model="good-model")]}
                ]}], partial)
                self.assertIsNone(report["total_usd"])
                self.assertEqual(report["known_subtotal_usd"], "0.00175")

    def test_unreviewed_accept_and_implicit_b_metrics_are_not_confirmed_correct(self):
        module = self.module()
        report = module.summarize_results([
            {"experiment": "A", "cases": [{"quality": "accept", "review_status": "unreviewed", "attempts": [attempt()]}]},
            {"experiment": "B", "cases": [{"quality": "accept", "review_status": "approved", "attempts": [attempt()]},
                                           {"review_status": "approved", "metrics": {"confirmed_correct_items": 2}, "attempts": [attempt()]}]}], self.pricing())
        self.assertEqual(report["efficiency"]["confirmed_correct_cases"], 0)
        self.assertEqual(report["efficiency"]["confirmed_correct_items"], 2)
        self.assertEqual(report["efficiency"]["cost_per_confirmed_correct_item_usd"], "0.00175")

    def test_cross_log_duplicate_is_visible_and_total_remains_unconfirmed(self):
        report = self.summarize([{"case_id": "a", "quality": "accept", "review_status": "approved",
                                 "attempts": [attempt(response_id="same")]}],
                                judge_audit=[{"attempts": [attempt(response_id="same")]}])
        self.assertEqual(report["counts"]["attempts"], 2)
        self.assertEqual(report["counts"]["ambiguous_cross_log_duplicates"], 1)
        self.assertIsNone(report["total_usd"])
        self.assertIsNone(report["efficiency"]["cost_per_confirmed_correct_case_usd"])
        self.assertIsNone(report["tokens"]["input_tokens"]["total"])

    def test_decimal_yaml_scalar_is_not_converted_through_binary_float(self):
        module = self.module()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as temporary:
            path = Path(temporary) / "prices.yaml"
            path.write_text('version: 1\ncurrency: USD\nunit: 1000000\nmodels:\n  test-model:\n'
                            '    input_usd_per_million: 0.12345678901234567890123456789\n'
                            '    output_usd_per_million: 0\n    source_url: https://example.test/prices\n'
                            '    checked_at: 2026-11-10\n    price_version: test\n', encoding="utf-8")
            pricing = module.load_pricing(path)
        report = module.summarize_results([{"cases": [{"attempts": [attempt(input_tokens=1_000_000)]}]}], pricing)
        self.assertEqual(report["total_usd"], "0.12345678901234567890123456789")

    def test_separate_b_exact_matches_requires_valid_denominator(self):
        module, pricing = self.module(), self.pricing()
        report = module.summarize_results([{"experiment": "B", "cases": [
            {"review_status": "approved", "metrics": {"exact_matches": 3}, "attempts": [attempt()]},
            {"review_status": "approved", "metrics": {"exact_matches": 2, "denominator": 10}, "attempts": [attempt()]},
            {"review_status": "unreviewed", "metrics": {"confirmed_correct_items": 9}, "attempts": [attempt()]},
        ]}], pricing)
        self.assertEqual(report["efficiency"]["confirmed_correct_items"], 2)

    def test_explicit_retry_flag_and_distinct_charged_attempts_are_kept(self):
        report = self.summarize([{"attempts": [attempt(response_id="x"),
                                               attempt(attempt=2, schema_version="other", is_retry=True, response_id="x")]}])
        self.assertEqual(report["counts"]["attempts"], 2)
        self.assertEqual(report["total_usd"], "0.0035")
        self.assertEqual(report["waste"]["retry_cost_usd"], "0.00175")

    def test_per_model_report_includes_cost_latency_correctness_and_failure_counts(self):
        report = self.summarize([{"case_id": "a", "status": "succeeded", "latency_ms": 100,
                                 "review_status": "approved", "quality": "accept", "attempts": [attempt()]},
                                {"case_id": "b", "status": "failed", "latency_ms": 300, "attempts": [attempt()]}])
        model = report["models"]["test-model"]
        self.assertEqual(model["counts"]["executed_cases"], 2)
        self.assertEqual(model["counts"]["service_failures"], 1)
        self.assertEqual(model["averages"]["service_per_case_usd"], "0.00175")
        self.assertEqual(model["efficiency"]["cost_per_confirmed_correct_case_usd"], "0.0035")
        self.assertEqual(model["efficiency"]["cost_per_confirmed_correct_usd"], "0.0035")
        self.assertEqual(model["latency_ms"]["p50"], 200)
        self.assertEqual(model["waste"]["retry_or_failure_cost_usd"], "0.00175")
        self.assertIsNone(model["score_deviation"])
        self.assertIsNone(model["quality"]["service_score_deviation"])

    def test_checkpoint_nested_judge_attempts_are_not_lost_or_finally_double_billed(self):
        module, pricing = self.module(), self.pricing()
        row = {"case_id": "a", "attempts": [attempt(response_id="service")],
               "judge": {"attempts": [attempt(response_id="judge")]}}
        checkpoint = module.summarize_results([{"cases": [row]}], pricing)
        self.assertEqual(checkpoint["judge"]["total_usd"], "0.00175")
        self.assertEqual(checkpoint["total_usd"], "0.0035")
        final = module.summarize_results([{"cases": [row], "judge_audit": [
            {"attempts": [attempt(response_id="judge")]}]}], pricing)
        self.assertEqual(final["counts"]["attempts"], 2)
        self.assertEqual(final["total_usd"], "0.0035")
        self.assertEqual(final["counts"]["reconciled_nested_judge_attempts"], 1)

    def test_nested_judge_without_attempt_audit_marks_billing_unconfirmed(self):
        report = self.summarize([{"case_id": "a", "attempts": [attempt()],
                                 "judge": {"failure": None, "metadata": {"latency_ms": 20}}}])
        self.assertIsNone(report["total_usd"])
        self.assertEqual(report["counts"]["incomplete_judge_audits"], 1)

    def test_interrupted_configured_judge_may_have_unlogged_control_cost(self):
        report = self.summarize([{"case_id": "a", "attempts": [attempt()],
                                 "judge": {"attempts": [attempt(response_id="judge")]}}],
                                run_state="interrupted", metadata={"max_judge_attempts": 10,
                                "grader": {"kind": "bounded_llm_judge"}})
        self.assertIsNone(report["total_usd"])
        self.assertGreaterEqual(report["counts"]["incomplete_judge_audits"], 1)

    def test_interrupted_judge_without_nested_logs_is_unknown_overhead_not_zero(self):
        report = self.summarize([{"case_id": "a", "attempts": [attempt()]}],
                                run_state="interrupted", metadata={"max_judge_attempts": 10})
        self.assertEqual(report["judge"]["status"], "unconfirmed")
        self.assertIsNone(report["averages"]["judge_overhead_per_case_usd"])

    def test_same_response_id_in_overlapping_result_files_is_not_confirmed(self):
        module, pricing = self.module(), self.pricing()
        run = {"cases": [{"case_id": "a", "attempts": [attempt(response_id="overlap")]}]}
        report = module.summarize_results([run, run], pricing)
        self.assertEqual(report["counts"]["attempts"], 2)
        self.assertIsNone(report["total_usd"])
        self.assertEqual(report["counts"]["ambiguous_cross_log_duplicates"], 1)

    def test_preflight_failures_are_separate_from_executed_service_failures(self):
        report = self.summarize([{"status": "failed", "attempts": []},
                                 {"status": "failed", "attempts": [attempt()]}])
        self.assertEqual(report["counts"]["service_failures"], 1)
        self.assertEqual(report["counts"]["preflight_failures"], 1)

    def test_latencies_ignore_dry_case_and_include_failed_measurements(self):
        report = self.summarize([{"status": "validated_only", "latency_ms": 0},
                                 {"status": "failed", "service_latency_ms": 100, "attempts": [attempt()]},
                                 {"status": "succeeded", "latency_ms": 300, "attempts": [attempt()]}])
        self.assertEqual(report["latency_ms"], {"p50": 200, "p95": 290, "measured_cases": 2})

    def test_estimate_uses_call_ranges_and_output_upper_only(self):
        report = self.module().estimate_cost("test-model", input_tokens_lower=1000, input_tokens_upper=2000,
                                             output_tokens_upper=100, calls_lower=1, calls_upper=2, pricing=self.pricing())
        self.assertEqual(report["expected_lower_usd"], "0.00125")
        self.assertEqual(report["expected_upper_usd"], "0.006")

    def test_estimate_distinct_rates_use_conservative_upper_without_discount_guess(self):
        report = self.module().estimate_cost("test-model", input_tokens_lower=1000, input_tokens_upper=2000,
                                             output_tokens_upper=100, calls_lower=1, calls_upper=2,
                                             pricing=self.pricing(price(cached_input_usd_per_million="0.25")))
        self.assertIsNone(report["expected_lower_usd"])
        self.assertEqual(report["expected_upper_usd"], "0.006")
        self.assertEqual(report["status"], "unconfirmed")


class BudgetTests(unittest.TestCase):
    def module(self):
        self.assertTrue((LAB / "cost_accounting.py").is_file(), "cost accounting implementation missing")
        return importlib.import_module("cost_accounting")

    def budget(self, **changes):
        return self.module().CostBudget(**{"amount_usd": Decimal("0.1"), "max_attempts": 2,
                                          "approval_id": "offline-simulation", **changes})

    def test_reservation_before_operation_enforces_dollars_and_retry_attempt_cap(self):
        module, budget = self.module(), self.budget()
        operations = []
        def operation():
            operations.append("ran")
            return {"cost": "0.03"}
        module.run_guarded_attempt(budget, Decimal("0.06"), operation, lambda result: Decimal(result["cost"]))
        module.run_guarded_attempt(budget, Decimal("0.06"), operation, lambda result: Decimal(result["cost"]))
        with self.assertRaises(module.BudgetRejected):
            module.run_guarded_attempt(budget, Decimal("0.01"), operation, lambda result: Decimal(result["cost"]))
        self.assertEqual(len(operations), 2)
        self.assertEqual(budget.to_dict()["spent_usd"], "0.06")
        budget = self.budget(max_attempts=100)
        ticket = budget.reserve(Decimal("0.08"))
        with self.assertRaises(module.BudgetRejected):
            module.run_guarded_attempt(budget, Decimal("0.03"), operation, lambda result: Decimal("0.01"))
        self.assertEqual(len(operations), 2)
        budget.settle(ticket, Decimal("0.02"))

    def test_atomic_concurrent_reservations_cannot_oversubscribe_inflight_spend(self):
        module, budget = self.module(), self.budget(max_attempts=10)
        def reserve():
            try:
                return budget.reserve(Decimal("0.06"))
            except module.BudgetRejected:
                return None
        with ThreadPoolExecutor(max_workers=8) as executor:
            tickets = list(executor.map(lambda _: reserve(), range(8)))
        self.assertEqual(sum(ticket is not None for ticket in tickets), 1)
        self.assertEqual(budget.to_dict()["reserved_usd"], "0.06")

    def test_actual_overrun_and_unknown_cost_halt_future_attempts(self):
        module = self.module()
        for actual in (Decimal("0.11"), None):
            with self.subTest(actual=actual):
                budget = self.budget(max_attempts=10)
                ticket = budget.reserve(Decimal("0.01"))
                budget.settle(ticket, actual)
                with self.assertRaises(module.BudgetRejected):
                    budget.reserve(Decimal("0.01"))
                self.assertTrue(budget.to_dict()["halted"])

    def test_high_precision_reservation_cannot_round_an_overrun_down_to_cap(self):
        module, budget = self.module(), self.budget()
        with self.assertRaises(module.BudgetRejected):
            budget.reserve(Decimal("0.10000000000000000000000000001"))

    def test_operation_error_keeps_unknown_spend_halted(self):
        module, budget = self.module(), self.budget()
        def operation():
            raise RuntimeError("offline failure")
        with self.assertRaises(RuntimeError):
            module.run_guarded_attempt(budget, Decimal("0.01"), operation, lambda _: Decimal("0"))
        self.assertEqual(budget.to_dict()["unknown_attempts"], 1)
        self.assertTrue(budget.to_dict()["halted"])

    def test_budget_requires_decimal_positive_cap_attempts_and_explicit_approval(self):
        module = self.module()
        for changes in ({"amount_usd": Decimal("0")}, {"amount_usd": 0.1}, {"max_attempts": True},
                        {"max_attempts": 0}, {"approval_id": " "}, {"amount_usd": Decimal("NaN")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.budget(**changes)
        budget = module.CostBudget(amount_usd=Decimal("1"), max_attempts=1, approved=True)
        with self.assertRaises(ValueError):
            budget.reserve(None)
        with self.assertRaises(ValueError):
            budget.reserve(Decimal("-1"))
        ticket = budget.reserve(Decimal("0"))
        budget.settle(ticket, Decimal("0"))
        with self.assertRaises(ValueError):
            budget.settle(ticket, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
