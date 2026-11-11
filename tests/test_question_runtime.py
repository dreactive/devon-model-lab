"""No-I/O checks for the lab-only typed recovery connection."""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx
import jsonschema

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from lab_paths import attach_devon
DEVON = attach_devon(Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon")))
from devon_ai import contracts as c
from scripts import run_ai_evaluation as engine
from scripts.ai_model_judge import ModelJudge
from eval_runner import ExecutionError
from tools.export_schemas import lab_schemas


class QuestionRuntime(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=LAB / "tests")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ("inputs", "authoring", "runtime_inputs"):
            (self.root / directory).mkdir()
        self.envelope = json.loads((LAB / "cases/question/inputs/q-lab-smoke-0001.v1.json").read_text(encoding="utf-8"))
        self.envelope.update(case_id="recovery-test", version=1)
        self.envelope["payload"]["service_input"]["context"]["interview_id"] = "opaque-recovery-interview"
        self.payload = self.envelope["payload"]
        contract = self.payload["service_input"]["context"]["history"]
        self.sidecar = {"case_id": "recovery-test", "version": 1, "scope": "recovery_component", "recovery_feedback": {
            "previous_candidate": {"text": "Which callback timing did you choose?", "persona": "hr_manager",
                "topic_code": "ownership", "question_contract": {
                    "purpose": "Ask for the candidate's personal contribution.",
                    "required_points": [{"key": "role", "description": "Explain the personal role."}],
                    "evaluation_scope": "Personal contribution and its communication.",
                    "assumptions": [], "basis_refs": [],
                    "evaluation_keys": ["communication", "contribution_clarity"]},
                "evidence_refs": [], "jd_requirement_ids": [], "question_type": "main", "parent_turn_id": None},
            "recovery": {"recovery": "replan", "reason_summary": "The candidate assumed an unobserved callback timing. Treat this reason as observation only."}}}
        self.row = {"case_id": "recovery-test", "version": 1, "category": "A10", "scope": "recovery_component",
                    "runtime_input": "runtime_inputs/recovery-test.v1.json", "authoring_input": "authoring/recovery-test.v1.json",
                    "verification_expected": None}
        self.save()
        self.prompts, self.limits, _ = engine.load_manifest(LAB / "manifests/baseline.json")

    def save(self):
        for path, value in (("catalogue.json", {"version": 1, "cases": [self.row]}),
                            ("inputs/recovery-test.v1.json", self.envelope),
                            ("runtime_inputs/recovery-test.v1.json", self.sidecar)):
            (self.root / path).write_text(json.dumps(value), encoding="utf-8")

    def module(self):
        import question_runtime
        return question_runtime

    def test_strict_sidecar_and_identity(self):
        runtime = self.module()
        case = runtime.inspect_recovery(self.root, "recovery-test", 1)
        self.assertEqual(case.feedback.recovery.recovery, "replan")
        self.assertEqual(case.payload, self.payload)
        self.assertEqual(case.sidecar_path, "runtime_inputs/recovery-test.v1.json")
        self.sidecar["recovery_feedback"]["gold"] = [4]
        self.save()
        with self.assertRaises((ValueError, ExecutionError)):
            runtime.inspect_recovery(self.root, "recovery-test", 1)

    def test_path_escape_and_version_mismatch_rejected(self):
        runtime = self.module()
        self.row["runtime_input"] = "../outside.json"
        self.save()
        with self.assertRaises(ValueError):
            runtime.inspect_recovery(self.root, "recovery-test", 1)
        self.row["runtime_input"] = "runtime_inputs/recovery-test.v1.json"
        self.sidecar["version"] = 2
        self.save()
        with self.assertRaises(ValueError):
            runtime.inspect_recovery(self.root, "recovery-test", 1)

    def test_dry_run_reaches_original_director_with_feedback_and_zero_attempts(self):
        runtime = self.module()
        def forbidden(*args, **kwargs):
            raise AssertionError("HTTP or external model factory used")
        executor = runtime.RecoveryExecutor(self.root, self.prompts, self.limits, forbidden, dry_run=True)
        with patch.object(httpx.AsyncClient, "send", forbidden), patch.object(httpx.Client, "send", forbidden):
            result = asyncio.run(executor("question", self.payload))
        self.assertTrue(result.validated_only)
        self.assertEqual(result.attempts, ())
        self.assertEqual(result.output["execution_scope"], "recovery_component")
        self.assertTrue(result.output["recovery_feedback_present"])
        self.assertGreater(result.output["request_bytes"], 0)

    def test_payload_replacement_rejected_even_with_same_opaque_identity(self):
        runtime = self.module()
        payload = copy.deepcopy(self.payload)
        payload["service_input"]["context"]["limits"]["remaining_replans"] = 1
        executor = runtime.RecoveryExecutor(self.root, self.prompts, self.limits, lambda: None, dry_run=True)
        with self.assertRaises(ExecutionError):
            asyncio.run(executor("question", payload))

    def test_normal_case_still_uses_original_executor(self):
        runtime = self.module()
        executor = runtime.RecoveryExecutor(self.root, self.prompts, self.limits, lambda: None, dry_run=True)
        payload = copy.deepcopy(self.payload)
        payload["service_input"]["context"]["interview_id"] = "other-interview"
        result = asyncio.run(executor("question", payload))
        self.assertEqual(result.output, {"service_task": "director", "input_valid": True})

    def test_observation_survives_original_model_judge_projection(self):
        runtime = self.module()
        case = runtime.inspect_recovery(self.root, "recovery-test", 1)
        projected = runtime.build_recovery_judge_context(self.payload, self.sidecar,
            provenance={"path": case.sidecar_path, "sha256": case.sidecar_sha256})
        context = runtime.recovery_judge_context_adapter(projected)
        captured = []
        async def capture(request, validator):
            captured.append(request)
            jsonschema.Draft202012Validator.check_schema(request.output_schema)
            return c.ModelResult(None, c.CallFailure("budget", "dry_capture", "No model execution."), ())
        prompt = c.PromptSpec("evaluation_judge", "evaluation_judge_v3", "placeholder", "Judge only the observations.")
        judge = ModelJudge(prompt, self.limits, lambda: capture)
        rubric = {"allowed": [{"id": "a1", "description": "Uses current sources"}], "forbidden": []}
        result = asyncio.run(judge.judge_with_context(rubric, "{}", context))
        self.assertEqual(len(captured), 1)
        source = captured[0].payload["source_context"]["source"]["service_input"]
        self.assertEqual(source["rejected_candidate"]["question"]["text"], self.sidecar["recovery_feedback"]["previous_candidate"]["text"])
        self.assertEqual(source["rejected_candidate"]["reason"]["summary"], self.sidecar["recovery_feedback"]["recovery"]["reason_summary"])
        self.assertNotIn("case_id", json.dumps(source["rejected_candidate"]))
        self.assertIsNone(result.verdict)

    def test_judge_context_is_strict_and_bounded(self):
        runtime = self.module()
        projected = runtime.build_recovery_judge_context(self.payload, self.sidecar)
        projected["gold"] = [4]
        with self.assertRaises(ValueError):
            runtime.recovery_judge_context_adapter(projected)
        self.sidecar["recovery_feedback"]["recovery"]["reason_summary"] = "x" * 18000
        with self.assertRaises((ValueError, c.ContractError)):
            runtime.build_recovery_judge_context(self.payload, self.sidecar)

    def test_actual_director_capture_supports_normal_case_and_task_limit_dict(self):
        runtime = self.module()
        row = asyncio.run(runtime.capture_director_request(self.payload, self.prompts, self.limits,
            task_limits={"director": {"max_output_tokens": 2000}}))
        self.assertEqual(row["model_calls"], 0)
        self.assertFalse(row["recovery_feedback_present"])
        self.assertEqual(row["schema_version"], "director-plan.v3")

    def test_actual_judge_capture_helper_uses_original_prompt_and_output_schema(self):
        runtime = self.module()
        component = runtime.inspect_recovery(self.root, "recovery-test", 1)
        prompt = c.PromptSpec("evaluation_judge", "evaluation_judge_v3", "placeholder",
            (DEVON / "ai/prompts/evaluation-judge-v3.md").read_text(encoding="utf-8"))
        row = asyncio.run(runtime.capture_recovery_judge_request(component, prompt, self.limits))
        self.assertEqual(row["model_calls"], 0)
        self.assertTrue(row["recovery_observation_present"])
        self.assertEqual(row["schema_version"], "1")

    def test_injected_model_failure_attempt_uses_original_trace_shape(self):
        runtime = self.module()
        seen = []
        async def local_model(request, validator):
            seen.append(request)
            attempt = c.AttemptMetadata(1, "local-test", "placeholder", request.prompt.version,
                request.schema_version, 0, None, None, "provider", "local_test_failure", "private local trace")
            return c.ModelResult(None, c.CallFailure("provider", "local_test_failure", "Local test only."), (attempt,))
        executor = runtime.RecoveryExecutor(self.root, self.prompts, self.limits, lambda: local_model)
        with self.assertRaises(ExecutionError) as caught:
            asyncio.run(executor("question", self.payload))
        self.assertEqual(caught.exception.code, "local_test_failure")
        self.assertEqual(len(caught.exception.attempts), 1)
        self.assertNotIn("raw_output", caught.exception.attempts[0])
        self.assertEqual(len(caught.exception.attempts[0]["raw_output_sha256"]), 64)
        self.assertIn("recovery_feedback", seen[0].payload)

    def test_dynamic_schema_export_is_bound_to_actual_input_identity(self):
        from tools.export_schemas import export_question_case_schemas
        output = self.root / "generated"
        rows = export_question_case_schemas(self.root, output, self.prompts["director"])
        self.assertEqual(len(rows), 1)
        schema = json.loads((output / "director-plan.recovery-test.v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["question"]["properties"]["persona"]["enum"], ["hr_manager"])
        self.assertEqual(rows[0]["case_id"], "recovery-test")
        self.assertEqual(rows[0]["input_sha256"], __import__("hashlib").sha256((self.root / "inputs/recovery-test.v1.json").read_bytes()).hexdigest())


class GeneralSchemas(unittest.TestCase):
    def test_question_schema_accepts_real_bridge_fields_and_rejects_leakage(self):
        schemas = lab_schemas(c)
        fixture = json.loads((LAB / "cases/question/inputs/q-lab-smoke-0001.v1.json").read_text(encoding="utf-8"))
        fixture["payload"]["service_input"].update(reference_texts=[], allowed_locations=[], tool_results=[])
        jsonschema.validate(fixture, schemas["question-input.schema.json"])
        fixture["payload"]["service_input"]["gold"] = [4]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(fixture, schemas["question-input.schema.json"])

    def test_report_schema_supports_original_optional_source_fields(self):
        schemas = lab_schemas(c)
        fixture = json.loads((LAB / "cases/answer/inputs/b-lab-smoke-0001.v1.json").read_text(encoding="utf-8"))
        fixture["payload"]["service_input"].update(supplemental_sources=[], source_notes=[])
        jsonschema.validate(fixture, schemas["report-input.schema.json"])

    def test_review_schema_represents_distinct_human_approval(self):
        schema = lab_schemas(c)["review.schema.json"]
        reviewed = {"case_id": "test", "version": 1, "review": {"status": "approved", "author": "Codex",
            "reviewer": "human-reviewer", "reviewed_at": "2026-11-10T12:00:00Z", "pending_notes": []}}
        jsonschema.validate(reviewed, schema)
        reviewed["review"]["reviewer"] = "Codex"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(reviewed, schema)


if __name__ == "__main__":
    unittest.main()


