"""Behavior checks for the offline lab boundary; run with Python -B."""

from __future__ import annotations

import asyncio
import copy
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))
DEVON = Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon"))


@contextmanager
def no_provider_io():
    """Windows asyncio uses a loopback socketpair internally; block HTTP itself."""
    def forbidden(*args, **kwargs):
        raise AssertionError("provider I/O attempted")
    with patch.object(httpx.Client, "send", forbidden), \
         patch.object(httpx.AsyncClient, "send", forbidden), \
         patch.object(socket, "create_connection", forbidden):
        yield


class OfflineBoundaries(unittest.TestCase):
    def module(self, name: str):
        target = LAB / (name.replace(".", "/") + ".py")
        self.assertTrue(target.is_file(), f"Missing offline implementation: {name}")
        return importlib.import_module(name)

    def arguments(self, output: Path, cases: Path | None = None) -> list[str]:
        return [
            "--devon-root", str(DEVON), "--cases", str(cases or LAB / "cases/answer"),
            "--manifest", str(LAB / "manifests/baseline.json"), "--output", str(output),
        ]

    def test_execute_flag_is_rejected_before_any_work(self):
        result = subprocess.run(
            [sys.executable, "-B", str(LAB / "score_eval.py"),
             *self.arguments(LAB / "must-never-be-created.json"), "--execute"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments: --execute", result.stderr)
        self.assertFalse((LAB / "must-never-be-created.json").exists())

    def test_common_adapter_cannot_enable_provider_execution(self):
        responses = self.module("adapters.responses")
        with self.assertRaisesRegex(ValueError, "stage1_offline_only"):
            responses.ResponsesAdapter(dry_run=False)
        with no_provider_io():
            result = asyncio.run(responses.ResponsesAdapter().call(
                "placeholder-candidate", "system prompt", {"turns": []},
                {"type": "object", "additionalProperties": False},
            ))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.model_calls, 0)
        self.assertIsNone(result.data)

    def test_adapter_schema_errors_are_sanitized(self):
        responses = self.module("adapters.responses")
        with self.assertRaisesRegex(ValueError, "^adapter_envelope_invalid$"):
            asyncio.run(responses.ResponsesAdapter().call(
                "placeholder", "system", {}, {"type": "SECRET_INVALID_SCHEMA_47a1"},
            ))

    def test_output_collision_preserves_original_bytes(self):
        runner = self.module("score_eval")
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            output = Path(directory) / "existing.json"
            output.write_bytes(b"original result\n")
            code = runner.main(self.arguments(output, Path(directory) / "missing-cases"))
            self.assertNotEqual(code, 0)
            self.assertEqual(output.read_bytes(), b"original result\n")

    def test_devon_output_is_rejected_without_creating_a_file(self):
        runner = self.module("score_eval")
        output = DEVON / "offline-lab-must-not-write-47a1.json"
        self.assertFalse(output.exists())
        self.assertEqual(runner.main(self.arguments(output)), 1)
        self.assertFalse(output.exists())

    def test_source_group_cannot_leak_across_excluded_splits(self):
        runner = self.module("score_eval")
        original = json.loads((LAB / "cases/answer/inputs/b-lab-smoke-0001.v1.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            (root / "inputs").mkdir()
            (root / "inputs/b-lab-smoke-0001.v1.json").write_text(json.dumps(original), encoding="utf-8")
            leaked = copy.deepcopy(original)
            leaked["case_id"] = "b-lab-smoke-0002"
            leaked["control"]["split"] = "holdout"
            (root / "inputs/b-lab-smoke-0002.v1.json").write_text(json.dumps(leaked), encoding="utf-8")
            with self.assertRaisesRegex(runner.LabError, "source_group_split_overlap"):
                runner.load_inputs(root)

    def test_invalid_manifest_errors_do_not_echo_raw_values(self):
        runner = self.module("score_eval")
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            manifest = root / "bad-manifest.json"
            manifest.write_text('{"private":"SECRET_MUST_NOT_ECHO_47a1"}', encoding="utf-8")
            output = root / "result.json"
            args = self.arguments(output)
            args[args.index("--manifest") + 1] = str(manifest)
            self.assertEqual(runner.main(args), 1)
            report_text = output.read_text(encoding="utf-8")
            self.assertNotIn("SECRET_MUST_NOT_ECHO_47a1", report_text)
            self.assertEqual(json.loads(report_text)["run_error"]["code"], "manifest_invalid")
            self.assertEqual(json.loads(report_text)["summary"]["status"], "failed")

    def test_real_request_capture_is_offline_and_gold_isolated(self):
        runner = self.module("score_eval")
        fixture = LAB / "cases/answer"
        self.assertTrue((fixture / "inputs/b-lab-smoke-0001.v1.json").is_file())
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            copied = root / "cases"
            for folder in ("inputs", "gold", "reviews"):
                (copied / folder).mkdir(parents=True)
                for source in (fixture / folder).glob("*.json"):
                    (copied / folder / source.name).write_bytes(source.read_bytes())
            first, second = root / "first.json", root / "second.json"
            with no_provider_io():
                self.assertEqual(runner.main(self.arguments(first, copied)), 0)
                gold_path = copied / "gold/b-lab-smoke-0001.json"
                gold = json.loads(gold_path.read_text(encoding="utf-8"))
                gold[0]["rationale"] = "GOLD_MUST_NEVER_ENTER_REQUEST_47a1"
                gold_path.write_text(json.dumps(gold), encoding="utf-8")
                self.assertEqual(runner.main(self.arguments(second, copied)), 0)
            a, b = (json.loads(path.read_text(encoding="utf-8")) for path in (first, second))
            self.assertEqual(a["summary"]["status"], "validated_only")
            self.assertEqual(a["summary"]["model_calls"], 0)
            self.assertEqual(a["cases"][0]["turn_count"], 9)
            self.assertEqual(a["cases"][0]["rubric_rows"], 30)
            self.assertEqual(a["cases"][0]["request"]["payload_sha256"],
                             b["cases"][0]["request"]["payload_sha256"])
            self.assertEqual(a["cases"][0]["request"]["task_name"], "report_score")
            self.assertIn("schema_enforced_by_provider", a["cases"][0]["request"])
            self.assertIsNone(a["cases"][0]["request"]["schema_enforced_by_provider"])
            self.assertNotIn("GOLD_MUST_NEVER_ENTER_REQUEST_47a1", second.read_text(encoding="utf-8"))
            self.assertNotIn("quality", a["summary"])

    def test_input_extras_and_incomplete_gold_are_rejected(self):
        runner = self.module("score_eval")
        fixture = LAB / "cases/answer"
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            copied = root / "cases"
            for folder in ("inputs", "gold", "reviews"):
                (copied / folder).mkdir(parents=True)
                for source in (fixture / folder).glob("*.json"):
                    (copied / folder / source.name).write_bytes(source.read_bytes())
            input_path = copied / "inputs/b-lab-smoke-0001.v1.json"
            original = json.loads(input_path.read_text(encoding="utf-8"))
            leaked = copy.deepcopy(original)
            leaked["payload"]["service_input"]["gold"] = [{"level": 4}]
            input_path.write_text(json.dumps(leaked), encoding="utf-8")
            self.assertEqual(runner.main(self.arguments(root / "extra.json", copied)), 1)
            self.assertEqual(json.loads((root / "extra.json").read_text(encoding="utf-8"))["summary"]["status"], "failed")
            input_path.write_text(json.dumps(original), encoding="utf-8")
            gold_path = copied / "gold/b-lab-smoke-0001.json"
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            gold_path.write_text(json.dumps(gold[:-1]), encoding="utf-8")
            output = root / "incomplete.json"
            self.assertEqual(runner.main(self.arguments(output, copied)), 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["cases"][0]["error"]["code"], "annotation_contract_invalid")
            self.assertEqual(report["summary"]["status"], "rejected")

    def test_not_applicable_uses_scope_rationale_without_a_numeric_rubric_quote(self):
        runner = self.module("score_eval")
        fixture = LAB / "cases/answer"
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory)
            copied = root / "cases"
            for folder in ("inputs", "gold", "reviews"):
                (copied / folder).mkdir(parents=True)
                for source in (fixture / folder).glob("*.json"):
                    (copied / folder / source.name).write_bytes(source.read_bytes())
            input_path = copied / "inputs/b-lab-smoke-0001.v1.json"
            envelope = json.loads(input_path.read_text(encoding="utf-8"))
            turn = envelope["payload"]["service_input"]["turns"][7]
            turn["persona"] = "domain_lead"
            turn["question"] = "Describe only the observable hold, confirmation, and expiry behavior of this fictional reservation domain."
            turn["question_contract"].update(
                evaluation_keys=[],
                purpose="Elicit a description of observable reservation-domain behavior; no JD-to-experience connection is requested.",
                evaluation_scope="Describe domain observations and assess communication. The question does not ask for a connection between JD requirements and personal experience.",
            )
            input_path.write_text(json.dumps(envelope), encoding="utf-8")
            gold_path = copied / "gold/b-lab-smoke-0001.json"
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            item = next(row for row in gold if row["turn_id"] == "8" and row["key"] == "project_understanding")
            item.update(key="company_job_fit", level="not_applicable",
                        rationale="The question asks only about observable domain behavior; its scope does not ask for a connection between JD requirements and personal experience.")
            item.pop("rubric_quote")
            gold_path.write_text(json.dumps(gold), encoding="utf-8")
            valid_output = root / "scope-na.json"
            with no_provider_io():
                self.assertEqual(runner.main(self.arguments(valid_output, copied)), 0)
            report = json.loads(valid_output.read_text(encoding="utf-8"))
            self.assertEqual(report["cases"][0]["annotations"]["status"], "contract_valid_only")
            self.assertEqual(report["cases"][0]["request"]["status"], "captured_only")
            self.assertEqual(report["summary"]["model_calls"], 0)
            item["rubric_quote"] = "요구사항과 본인 경험을 구체적 사례로 연결한다."
            gold_path.write_text(json.dumps(gold), encoding="utf-8")
            invalid_output = root / "na-with-numeric-quote.json"
            self.assertEqual(runner.main(self.arguments(invalid_output, copied)), 1)
            rejected = json.loads(invalid_output.read_text(encoding="utf-8"))
            self.assertEqual(rejected["cases"][0]["error"]["code"], "annotation_contract_invalid")


if __name__ == "__main__":
    unittest.main()
