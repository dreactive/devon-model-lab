"""Offline approval tests; all rates, people and endpoints below are fictional."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from execution_policy import (
    SOURCE_REQUIRED, PolicyError, build_plan, claim_approval, plan_digest,
    read_json, validate_execution,
)


class ExecutionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "runs")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devon = self.root / "readonly-devon"
        self.lab = self.root / "model-lab"
        self.lab.mkdir()
        for relative in SOURCE_REQUIRED:
            path = self.devon / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fictional source fixture\n", encoding="utf-8")
        self.prompt = self.devon / "ai/prompts/director.md"
        self.prompt.parent.mkdir(parents=True, exist_ok=True)
        self.prompt.write_text("Fictional director prompt", encoding="utf-8")
        self.write(self.devon / "ai/prompts/runtime-prompts.json", {
            "director": {"version": "v1", "template": "director.md"},
            "report_score": {"version": "v1", "template": "director.md"},
        })
        self.cases = self.lab / "cases/question"
        self.input = self.cases / "inputs/one.v1.json"
        self.expectation = self.cases / "expectations/one.v1.json"
        self.write(self.input, {"case_id": "one", "version": 1,
            "control": {"kind": "question", "split": "dev"}, "payload": {}})
        self.write(self.expectation, {"case_id": "one", "review": {"status": "unreviewed"}})
        self.manifest = self.lab / "manifest.json"
        self.write(self.manifest, {"prompts": [
            {"task_name": name, "version": "v1", "model": model,
             "template_path": str(self.prompt)}
            for name, model in (("director", "fictional-model"),
                                ("report_score", "different-unused-model"))],
            "limits": {"timeout_seconds": 10, "max_output_tokens": 20,
                       "max_input_bytes": 1000, "max_response_bytes": 2000}})
        self.pricing = self.lab / "prices.yaml"
        self.pricing.write_text("""version: 1
currency: USD
unit: 1000000
models:
  fictional-model:
    input_usd_per_million: '1'
    output_usd_per_million: '2'
    cached_input_usd_per_million: '1'
    reasoning_output_usd_per_million: '2'
    source_url: https://example.invalid/fictional-rates
    checked_at: '2026-11-10'
    price_version: fixture-only
""", encoding="utf-8")
        self.now = datetime.now(timezone.utc)
        self.approval = self.lab / "fictional-approval.json"
        self.kwargs = dict(devon_root=self.devon, lab_root=self.lab, cases_path=self.cases,
            manifest_path=self.manifest, pricing_path=self.pricing,
            experiment="A", split="dev", repeats=1, budget_usd=Decimal("0.01"),
            max_http_attempts=3, base_url="https://example.invalid/v1")

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def approve(self, plan, **updates):
        approval = {"version": 1, "approved": True, "plan_sha256": plan_digest(plan),
            "approved_by": "Fictional fixture operator", "approved_at": self.now.isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat()}
        approval.update(updates)
        self.write(self.approval, approval)

    def validate(self, plan, **updates):
        kwargs = {key: self.kwargs[key] for key in
            ("devon_root", "cases_path", "manifest_path", "pricing_path", "base_url")}
        kwargs.update(approval_path=self.approval, now=self.now)
        kwargs.update(updates)
        return validate_execution(plan, **kwargs)

    def test_complete_plan_validates_and_selects_only_executable_model(self):
        plan = build_plan(**self.kwargs)
        self.assertEqual(plan["blocked_reasons"], [])
        self.assertEqual(plan["model_ids"], ["fictional-model"])
        self.assertEqual(Decimal(plan["expected_upper_usd"]), Decimal("0.00312"))
        self.assertEqual(plan["expected_lower_usd"], "0")
        self.approve(plan)
        policy = self.validate(plan)
        self.assertEqual(policy.budget_usd, Decimal("0.01"))
        self.assertEqual(policy.max_http_attempts, 3)
        self.assertEqual(policy.model_ids, frozenset({"fictional-model"}))
        self.assertEqual(policy.plan_sha256, plan_digest(plan))

    def test_optional_cached_and_reasoning_rates_can_remain_null(self):
        rates = self.pricing.read_text().replace("cached_input_usd_per_million: '1'",
            "cached_input_usd_per_million: null").replace("reasoning_output_usd_per_million: '2'",
            "reasoning_output_usd_per_million: null")
        self.pricing.write_text(rates, encoding="utf-8")
        plan = build_plan(**self.kwargs)
        self.assertEqual(plan["blocked_reasons"], [])
        self.assertEqual(Decimal(plan["expected_upper_usd"]), Decimal("0.00312"))
        self.approve(plan)
        self.validate(plan)

    def test_prepare_missing_budget_and_prices_is_blocked_and_unexecutable(self):
        self.pricing.write_text(self.pricing.read_text().replace("'1'", "null"), encoding="utf-8")
        plan = build_plan(**(self.kwargs | {"budget_usd": None, "max_http_attempts": None}))
        self.assertIn("budget_missing", plan["blocked_reasons"])
        self.assertIn("http_attempt_cap_missing", plan["blocked_reasons"])
        self.assertIn("model_price_incomplete", plan["blocked_reasons"])
        self.approve(plan)
        with self.assertRaises(PolicyError):
            self.validate(plan)

    def test_every_data_criterion_and_resolved_prompt_change_invalidates(self):
        for target in (self.input, self.expectation, self.prompt, self.manifest, self.pricing,
                       self.devon / SOURCE_REQUIRED[0]):
            with self.subTest(target=target.name):
                original = target.read_bytes()
                plan = build_plan(**self.kwargs)
                self.approve(plan)
                target.write_bytes(original + b"\n")
                with self.assertRaises(PolicyError):
                    self.validate(plan)
                target.write_bytes(original)

    def test_new_dataset_file_invalidates(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        self.write(self.cases / "reviews/new.json", {"status": "unreviewed"})
        with self.assertRaises(PolicyError):
            self.validate(plan)

    def test_lab_runtime_and_schema_changes_require_fresh_approval(self):
        runtime = self.lab / "question_runtime.py"
        schema = self.lab / "schemas/question-input.schema.json"
        runtime.write_text("# offline fixture runtime", encoding="utf-8")
        self.write(schema, {"type": "object"})
        for target in (runtime, schema):
            with self.subTest(target=target.name):
                plan = build_plan(**self.kwargs)
                self.approve(plan)
                previous = target.read_bytes()
                target.write_bytes(previous + b"\n")
                with self.assertRaises(PolicyError):
                    self.validate(plan)
                target.write_bytes(previous)

    def test_b_plan_binds_gold_and_review_without_embedding_them(self):
        data = json.loads(self.input.read_text())
        data["control"]["kind"] = "report"
        self.write(self.input, data)
        manifest = json.loads(self.manifest.read_text())
        manifest["prompts"][1]["model"] = "fictional-model"
        self.write(self.manifest, manifest)
        gold, review = self.cases / "gold/one.json", self.cases / "reviews/one.json"
        self.write(gold, [{"acceptable": "FICTIONAL PRIVATE GOLD VALUE"}])
        self.write(review, {"status": "unreviewed"})
        for target in (gold, review):
            with self.subTest(target=target.name):
                plan = build_plan(**(self.kwargs | {"experiment": "B"}))
                self.assertNotIn("FICTIONAL PRIVATE GOLD VALUE", json.dumps(plan))
                self.approve(plan)
                self.assertEqual(self.validate(plan).model_ids, frozenset({"fictional-model"}))
                raw = target.read_bytes()
                target.write_bytes(raw + b"\n")
                with self.assertRaises(PolicyError):
                    self.validate(plan)
                target.write_bytes(raw)

    def test_changed_plan_values_or_route_reject_before_claim(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        for field, value in (("budget_usd", "100"), ("max_http_attempts", 100),
                             ("split", "holdout"), ("repeats", 2)):
            with self.subTest(field=field), self.assertRaises(PolicyError):
                self.validate(plan | {field: value})
        with self.assertRaises(PolicyError):
            self.validate(plan, base_url="https://other.example.invalid/v1")

    def test_approval_requires_exact_hash_expiry_identity_and_timezone(self):
        plan = build_plan(**self.kwargs)
        for update in ({"plan_sha256": "0" * 64}, {"approved": False},
                       {"approved_by": " "}, {"approved_at": "2026-11-10T00:00:00"},
                       {"expires_at": self.now.isoformat()},
                       {"approved_at": (self.now + timedelta(minutes=1)).isoformat()},
                       {"version": True}):
            with self.subTest(update=update):
                self.approve(plan, **update)
                with self.assertRaises(PolicyError):
                    self.validate(plan)

    def test_claim_is_exclusive_and_contained_in_lab_runs(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        policy = self.validate(plan)
        claim_root = self.lab / "runs/.approval-claims"
        claim = claim_approval(policy, claim_root=claim_root)
        self.assertTrue(claim.is_file())
        with self.assertRaises(PolicyError):
            claim_approval(policy, claim_root=claim_root)
        with self.assertRaises(PolicyError):
            claim_approval(policy, claim_root=self.devon / "claims")
        with self.assertRaises(PolicyError):
            claim_approval(policy, claim_root=self.root / "elsewhere")

    def test_claim_rechecks_inputs_since_preflight(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        policy = self.validate(plan)
        self.prompt.write_text("Changed after validation", encoding="utf-8")
        with self.assertRaises(PolicyError):
            claim_approval(policy, claim_root=self.lab / "runs/.approval-claims")
        self.assertFalse((self.lab / "runs/.approval-claims").exists())

    def test_claim_rechecks_approval_since_preflight(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        policy = self.validate(plan)
        self.approve(plan, approved_by="A different fictional operator")
        with self.assertRaises(PolicyError):
            claim_approval(policy, claim_root=self.lab / "runs/.approval-claims")
        self.assertFalse((self.lab / "runs/.approval-claims").exists())

    def test_endpoint_requires_explicit_https_without_secret_fields(self):
        for value in (None, "http://example.invalid", "https://key@example.invalid/v1",
                      "https://example.invalid/v1?api_key=secret", "https://example.invalid/#fragment",
                      " https://example.invalid", "https://example.invalid:bad/v1"):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                build_plan(**(self.kwargs | {"base_url": value}))

    def test_bad_numeric_types_fail_closed(self):
        for key, values in (("budget_usd", (True, 0, -1, Decimal("NaN"), Decimal("Infinity"))),
                            ("max_http_attempts", (True, 0, -1, 1.5)),
                            ("repeats", (True, 0))):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(PolicyError):
                    build_plan(**(self.kwargs | {key: value}))

    def test_json_duplicate_keys_and_nonfinite_numbers_are_rejected(self):
        for raw in ('{"approved": true, "approved": false}', '{"value": NaN}',
                    '{"value": Infinity}', '{"value": 1e309}'):
            self.approval.write_text(raw, encoding="utf-8")
            with self.assertRaises(PolicyError):
                read_json(self.approval)

    def test_output_inside_devon_and_lab_inside_devon_are_rejected(self):
        plan = build_plan(**self.kwargs)
        self.approve(plan)
        with self.assertRaises(PolicyError):
            self.validate(plan, output_root=self.devon / "runs")
        with self.assertRaises(PolicyError):
            build_plan(**(self.kwargs | {"lab_root": self.devon / "model-lab"}))


if __name__ == "__main__":
    unittest.main()
