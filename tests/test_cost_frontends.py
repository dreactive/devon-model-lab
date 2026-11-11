"""Offline CLI integration checks; all rates in these tests are fictional."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import yaml

LAB = Path(__file__).resolve().parents[1]
DEVON = Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon"))


class CostFrontendTests(unittest.TestCase):
    def test_recovery_estimate_includes_the_actual_typed_feedback(self):
        from lab_paths import attach_devon
        attach_devon(DEVON)
        import cost_estimate
        from devon_ai.agents.director import runtime
        original = runtime._input_payload
        seen = []
        def capture(*args, **kwargs):
            payload, sources = original(*args, **kwargs)
            seen.append(payload)
            return payload, sources
        args = SimpleNamespace(experiment="A", manifest=LAB / "manifests/baseline.json",
            cases=LAB / "cases/question/benchmark-v1", split="all")
        with patch.object(runtime, "_input_payload", side_effect=capture):
            _, _, measured = cost_estimate.requests(args, DEVON)
        self.assertEqual(len(measured), 35)
        self.assertEqual(sum("recovery_feedback" in payload for payload in seen), 3)

    def invoke(self, script, arguments):
        environment = {**os.environ, "DEVON_ROOT": str(DEVON), "PYTHONIOENCODING": "cp949",
                       "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([sys.executable, "-B", str(LAB / script), *map(str, arguments)],
                              env=environment, cwd=LAB, capture_output=True, check=False)

    def test_estimate_is_cp949_safe_and_unpriced_not_invented(self):
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            output = Path(directory) / "estimate.json"
            result = self.invoke("cost_estimate.py", ["--experiment", "A", "--devon-root", DEVON,
                "--cases", LAB / "cases/question", "--manifest", LAB / "manifests/baseline.json",
                "--pricing", LAB / "pricing.yaml", "--max-model-attempts", "2", "--output", output])
            self.assertEqual(result.returncode, 0, result.stderr.decode("cp949", errors="replace"))
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertIsNone(report["estimated_upper_usd"])
            self.assertEqual(report["max_total_http_attempts"], 2)
            self.assertEqual(report["nominal_service_calls"], 2)
            self.assertFalse(report["execution_enabled"])
            self.assertFalse(report["approved"])
            self.assertGreater(report["input_measurements"][0]["serialized_request_bytes"], 0)

    def test_estimator_rejects_nonservice_prompt_before_writing(self):
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            manifest = json.loads((LAB / "manifests/baseline.json").read_text(encoding="utf-8"))
            for prompt in manifest["prompts"]:
                if prompt["task_name"] == "report_score":
                    prompt["version"] = "report_score_v2"
            source, output = root / "manifest.json", root / "estimate.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.invoke("cost_estimate.py", ["--experiment", "B", "--devon-root", DEVON,
                "--cases", LAB / "cases/answer", "--manifest", source, "--output", output])
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())

    def test_saved_attempts_produce_model_cost_and_parallel_columns(self):
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            price, source, output, rendered = [root / name for name in
                                                ("prices.yaml", "result.json", "cost.json", "cost.md")]
            price.write_text(yaml.safe_dump({"version": 1, "currency": "USD", "unit": 1000000,
                "models": {"fictional-test-model": {"input_usd_per_million": 2,
                    "output_usd_per_million": 6, "cached_input_usd_per_million": None,
                    "reasoning_output_usd_per_million": None, "source_url": "https://example.invalid/test-prices",
                    "checked_at": "2026-11-10", "price_version": "fictional-unit-test"}}}), encoding="utf-8")
            source.write_text(json.dumps({"cases": [{"case": "test-only", "kind": "question",
                "status": "succeeded", "review_status": "approved", "quality": "accept",
                "service_latency_ms": 123, "attempts": [{"attempt": 1, "provider": "test-only",
                    "model": "fictional-test-model", "prompt_version": "test", "schema_version": "test",
                    "input_tokens": 1000000, "output_tokens": 500000, "latency_ms": 123,
                    "error_stage": None, "error_code": None, "response_id": "fictional-test-only"}]}]}), encoding="utf-8")
            result = self.invoke("cost_report.py", ["--results", source, "--pricing", price,
                                                   "--output", output, "--markdown", rendered])
            self.assertEqual(result.returncode, 0, result.stderr.decode("cp949", errors="replace"))
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["total_usd"], "5")
            model = report["models"]["fictional-test-model"]
            self.assertEqual(model["averages"]["service_per_case_usd"], "5")
            self.assertEqual(model["latency_ms"]["p50"], 123)
            text = rendered.read_text(encoding="utf-8")
            self.assertIn("fictional-test-model | 5 | 5 | 5", text)
            self.assertIn("123/123", text)


if __name__ == "__main__":
    unittest.main()
