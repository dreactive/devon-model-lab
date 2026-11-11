"""Exercise both actual service call paths using only an in-memory transport."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
DEVON = Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon"))
sys.path.insert(0, str(LAB))


class RunnerTests(unittest.TestCase):
    def runner(self):
        self.assertTrue((LAB / "run_lab.py").exists(), "Guarded entry point missing")
        return importlib.import_module("run_lab")

    def execute(self, runner, root, plan, approval, env, delegate, name="result.json"):
        with patch.object(runner, "LAB_ROOT", root):
            return asyncio.run(runner.execute_approved_plan(plan, approval, env, root / "runs" / name, delegate=delegate))

    def prepare(self, directory, experiment="B", budget="10", attempts=2):
        from execution_policy import build_plan, plan_digest
        root = Path(directory)
        (root / "runs").mkdir(exist_ok=True)
        for name in ("cases", "schemas", "manifests"):
            shutil.copytree(LAB / name, root / name)
        price = {"version": 1, "currency": "USD", "unit": 1000000, "models": {
            "gpt-5.6-luna": {"input_usd_per_million": "1", "output_usd_per_million": "2",
                "source_url": "https://example.invalid/fictional", "checked_at": "2026-11-10",
                "price_version": "offline-fixture-only"}}}
        pricing = root / "pricing.yaml"
        pricing.write_text(json.dumps(price), encoding="utf-8")
        cases = root / "cases" / ("question" if experiment == "A" else "answer")
        plan = build_plan(devon_root=DEVON, lab_root=root, cases_path=cases,
            manifest_path=root / "manifests/baseline.json", pricing_path=pricing,
            experiment=experiment, split="all", base_url="https://example.invalid/v1",
            budget_usd=budget, max_http_attempts=attempts)
        plan_path = root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        now = datetime.now(timezone.utc)
        approval = {"version": 1, "approved": True, "plan_sha256": plan_digest(plan),
                    "approved_by": "offline-test-only", "approved_at": (now-timedelta(minutes=1)).isoformat(),
                    "expires_at": (now+timedelta(hours=1)).isoformat()}
        approval_path = root / "approval.json"
        approval_path.write_text(json.dumps(approval), encoding="utf-8")
        env = root / ".env"
        env.write_text("OPENAI_API_KEY=FAKE_OFFLINE_KEY_NEVER_LOG_481\nLLM_BASE_URL=https://example.invalid/v1\n", encoding="utf-8")
        return root, plan_path, approval_path, env

    def envelope(self, output, number=1, usage=True):
        result = {"id": f"fictional-{number}", "model": "gpt-5.6-luna", "status": "completed",
                  "output": [{"type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": json.dumps(output)}]}]}
        if usage:
            result["usage"] = {"input_tokens": 100, "output_tokens": 20}
        return result

    def test_missing_approval_blocks_before_transport_or_env_secret(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory)
            approval.unlink()
            sent = []
            delegate = httpx.MockTransport(lambda request: sent.append(request))
            with self.assertRaises(Exception):
                self.execute(runner, root, plan, approval, env, delegate)
            self.assertEqual(sent, [])
            self.assertFalse((root / "runs/.approval-claims").exists())

    def test_b_reuses_judge_scores_and_persists_guarded_spend_without_gold(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory)
            sent = []
            def handle(request):
                payload = json.loads(request.content)
                sent.append(payload)
                data = json.loads(payload["input"][0]["content"][0]["text"])
                self.assertNotIn("gold", data)
                judgments = [{"turn_id": turn["turn_id"], "key": key,
                              "level": 0 if turn["answer"] is None else 2}
                             for turn in data["turns"] for key in turn["candidate_keys"]]
                return httpx.Response(200, json=self.envelope({"judgments": judgments}))
            with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", side_effect=AssertionError("real network prohibited")):
                result = self.execute(runner, root, plan, approval, env, httpx.MockTransport(handle))
            self.assertEqual(len(sent), 1)
            self.assertEqual(result["run_state"], "completed")
            self.assertEqual(result["cases"][0]["status"], "succeeded")
            self.assertEqual(len(result["cases"][0]["output"]["judgments"]), 18)
            self.assertEqual(result["cost_budget"]["attempts_started"], 1)
            self.assertEqual(result["cost_budget"]["spent_usd"], "0.00014")
            self.assertNotIn("FAKE_OFFLINE_KEY_NEVER_LOG_481", (root / "runs/result.json").read_text(encoding="utf-8"))
            self.assertTrue(list((root / "runs/.approval-claims").glob("*")))
            with self.assertRaises(Exception):
                self.execute(runner, root, plan, approval, env, httpx.MockTransport(handle), "again.json")
            self.assertEqual(len(sent), 1)

    def test_a_original_engine_plan_and_review_share_guard(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory, "A")
            seen = []
            def handle(request):
                body = json.loads(request.content)
                payload = json.loads(body["input"][0]["content"][0]["text"])
                seen.append(payload["operation"])
                if payload["operation"] == "plan":
                    output = {"intent": "clarify", "reason_summary": "Ask about the candidate's role.", "question": {
                        "persona": "hr_manager", "text": "이 프로젝트에서 본인이 맡은 역할을 설명해 주세요.", "topic_code": "role",
                        "question_contract": {"purpose": "담당 역할 확인", "required_points": [{"key": "own_role", "description": "직접 담당한 역할"}],
                            "assumptions": [], "basis_refs": [], "evaluation_scope": "본인 역할과 설명의 명확성을 평가한다.",
                            "evaluation_keys": ["contribution_clarity", "communication"]},
                        "evidence_refs": [], "jd_requirement_ids": [], "question_type": "main", "parent_turn_id": None}}
                else:
                    output = {"plan_valid": True, "context_valid": True, "wording_valid": True,
                              "contract_matches": True, "safe_alternative": True, "reason_summary": "Scoped role question."}
                return httpx.Response(200, json=self.envelope(output, len(seen)))
            result = self.execute(runner, root, plan, approval, env, httpx.MockTransport(handle))
            self.assertEqual(seen, ["plan", "review"])
            self.assertEqual(result["cost_budget"]["attempts_started"], 2)
            self.assertEqual(result["cost_budget"]["spent_usd"], "0.00028")
            self.assertEqual(result["cases"][0]["status"], "succeeded")
            self.assertEqual(result["summary"]["quality_denominator"], 0)

    def test_unknown_usage_stops_entire_run_and_checkpoint_survives(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory, "A")
            sent = []
            def handle(request):
                sent.append(request)
                return httpx.Response(200, json=self.envelope({}, usage=False))
            result = self.execute(runner, root, plan, approval, env, httpx.MockTransport(handle))
            self.assertEqual(len(sent), 1)
            self.assertEqual(result["run_state"], "budget_stopped")
            self.assertTrue(result["cost_budget"]["halted"])
            self.assertEqual(result["cost_budget"]["unknown_attempts"], 1)
            self.assertEqual(json.loads((root / "runs/result.json").read_text(encoding="utf-8"))["run_state"], "budget_stopped")

    def test_a_recovery_sidecar_reaches_original_plan_under_same_http_guard(self):
        from execution_policy import build_plan, plan_digest
        runner = self.runner()
        corpus = LAB / "cases/question/benchmark-v1"
        catalogue = json.loads((corpus / "catalogue.json").read_text(encoding="utf-8"))
        rows = [row for row in catalogue["cases"] if row["scope"] == "recovery_component"]
        self.assertEqual(len(rows), 3)
        for row in rows:
            with self.subTest(case=row["case_id"]), tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
                root, plan_path, approval, env = self.prepare(directory, "A")
                selected = root / "selected-recovery"
                stem = f"{row['case_id']}.v{row['version']}.json"
                for relative in ("inputs/" + stem, "expectations/" + stem, row["authoring_input"], row["runtime_input"]):
                    target = selected / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(corpus / relative, target)
                (selected / "catalogue.json").write_text(json.dumps({"version": 1, "cases": [row]}), encoding="utf-8")
                plan = build_plan(devon_root=DEVON, lab_root=root, cases_path=selected,
                    manifest_path=root / "manifests/baseline.json", pricing_path=root / "pricing.yaml",
                    experiment="A", split="all", base_url="https://example.invalid/v1", budget_usd="10", max_http_attempts=2)
                plan_path.write_text(json.dumps(plan), encoding="utf-8")
                approved = json.loads(approval.read_text())
                approved["plan_sha256"] = plan_digest(plan)
                approval.write_text(json.dumps(approved), encoding="utf-8")
                requests = []
                def handle(request):
                    body = json.loads(request.content)
                    payload = json.loads(body["input"][0]["content"][0]["text"])
                    requests.append(payload)
                    return httpx.Response(200, json=self.envelope({}, usage=False))
                with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", side_effect=AssertionError("real network prohibited")):
                    result = self.execute(runner, root, plan_path, approval, env, httpx.MockTransport(handle))
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["operation"], "plan")
                self.assertIn("recovery_feedback", requests[0])
                sidecar = json.loads((selected / row["runtime_input"]).read_text(encoding="utf-8"))
                self.assertEqual(requests[0]["recovery_feedback"]["previous_candidate"], sidecar["recovery_feedback"]["previous_candidate"])
                self.assertEqual(result["run_state"], "budget_stopped")
                self.assertEqual(result["cost_budget"]["attempts_started"], 1)
                self.assertEqual(result["cost_budget"]["unknown_attempts"], 1)

    def test_changed_price_or_missing_budget_does_not_reach_transport(self):
        runner = self.runner()
        for change in ("price", "budget"):
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
                root, plan_path, approval, env = self.prepare(directory)
                if change == "price":
                    (root / "pricing.yaml").write_text("version: 1\ncurrency: USD\nunit: 1000000\nmodels: {}\n", encoding="utf-8")
                else:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    plan["budget_usd"] = None
                    plan_path.write_text(json.dumps(plan), encoding="utf-8")
                sent = []
                with self.assertRaises(Exception):
                    self.execute(runner, root, plan_path, approval, env, httpx.MockTransport(lambda request: sent.append(request)))
                self.assertEqual(sent, [])

    def test_shutdown_failure_still_records_terminal_budget_and_spend(self):
        runner = self.runner()
        class BrokenClose(httpx.MockTransport):
            async def aclose(self):
                raise RuntimeError("fake-close-error")
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory)
            def handle(request):
                data = json.loads(json.loads(request.content)["input"][0]["content"][0]["text"])
                judgments = [{"turn_id": turn["turn_id"], "key": key, "level": 0 if turn["answer"] is None else 2}
                             for turn in data["turns"] for key in turn["candidate_keys"]]
                return httpx.Response(200, json=self.envelope({"judgments": judgments}))
            result = self.execute(runner, root, plan, approval, env, BrokenClose(handle))
            self.assertNotEqual(result["run_state"], "running")
            self.assertNotEqual(result["run_state"], "completed")
            self.assertEqual(result["cost_budget"]["spent_usd"], "0.00014")
            self.assertTrue(result["cost_budget"]["halted"])
            self.assertEqual(json.loads((root / "runs/result.json").read_text(encoding="utf-8"))["run_state"], result["run_state"])

    def test_completed_run_with_failed_output_is_technical_failure(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root, plan, approval, env = self.prepare(directory)
            sent = []
            def handle(request):
                sent.append(request)
                return httpx.Response(200, json=self.envelope({}, len(sent)))
            result = self.execute(runner, root, plan, approval, env, httpx.MockTransport(handle))
            self.assertEqual(len(sent), 2)
            self.assertEqual(result["cases"][0]["status"], "failed")
            self.assertEqual(result["cost_budget"]["spent_usd"], "0.00028")
            self.assertEqual(runner.technical_exit_code(result), 1)

    def test_post_start_exception_does_not_claim_zero_api_calls(self):
        runner = self.runner()
        async def after_started(*args, **kwargs):
            raise OSError("fake-checkpoint-failure-after-send")
        with patch.object(runner, "execute_approved_plan", after_started), patch("builtins.print") as printed:
            code = runner.main(["--execute", "--plan", "unused", "--approval", "unused", "--output", "unused"])
        self.assertEqual(code, 1)
        printed_value = json.loads(printed.call_args[0][0])
        self.assertIsNone(printed_value.get("api_calls"))

    def test_linked_env_cannot_read_an_external_secret_file(self):
        runner = self.runner()
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            local, outside = root / "lab", root / "outside"
            local.mkdir()
            outside.mkdir()
            secret = outside / ".env"
            secret.write_text("OPENAI_API_KEY=FAKE_EXTERNAL_ONLY\nLLM_BASE_URL=https://example.invalid/v1\n", encoding="utf-8")
            link = local / ".env"
            try:
                link.symlink_to(secret)
            except OSError:
                self.skipTest("Windows file symlink privilege unavailable")
            with self.assertRaisesRegex(ValueError, "local_env_required"):
                runner._credentials(link, local)


if __name__ == "__main__":
    unittest.main()
