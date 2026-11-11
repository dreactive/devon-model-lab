"""Offline integration safeguards for the expanded synthetic corpus."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock
import asyncio

import run_lab
from lab_paths import attach_devon

attach_devon(Path("C:/Users/dreac/Desktop/kdt/devon"))


class RuntimeBindingTests(unittest.TestCase):
    def test_failed_executor_row_blocks_even_when_input_summary_passes(self):
        report = {"cases": [{"status": "failed", "error_stage": "executor"}],
                  "summary": {"automatic_checks": {"input_contract": {"passed": 1, "failed": 0}}}}
        plan = {"experiment": "A", "split": "all", "config": {}}
        with patch.object(run_lab, "dry_run_question", new=AsyncMock(return_value=report)):
            with self.assertRaisesRegex(ValueError, "input_precheck_rejected"):
                asyncio.run(run_lab._precheck(plan, Path("fictional-devon")))

    def test_recovery_executor_is_scoped_to_both_original_engine_routes(self):
        import question_runtime
        original = object()
        engine = SimpleNamespace(ServiceExecutor=original)
        root = Path("fictional-corpus")
        with patch.object(question_runtime, "RecoveryExecutor") as executor:
            with run_lab._bound_question_executor(engine, root):
                engine.ServiceExecutor("prompts", "limits", "factory", dry_run=True)
                executor.assert_called_once_with(root, "prompts", "limits", "factory", dry_run=True)
            self.assertIs(engine.ServiceExecutor, original)

    def test_executor_restores_after_failure(self):
        engine = SimpleNamespace(ServiceExecutor=object())
        original = engine.ServiceExecutor
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with run_lab._bound_question_executor(engine, Path("fictional")):
                raise RuntimeError("fixture")
        self.assertIs(engine.ServiceExecutor, original)


class CorpusIsolationTests(unittest.TestCase):
    def test_self_consistent_bundle_hash_cannot_replace_actual_model_source(self):
        from corpus_check import validate_bundle_binding
        bundle = {"repository_id": "repo", "git_ref": "ref", "files": [{"path": "src.py", "content": "unrelated"}]}
        payload = {"context": {"repositories": [{"repository_id": "repo", "git_ref": "ref"}],
            "evidence": [{"source_kind": "code", "path": "src.py", "content": "actual model source", "repository_id": "repo", "git_ref": "ref"}]}}
        with self.assertRaisesRegex(ValueError, "source_bundle_binding_mismatch"):
            validate_bundle_binding(bundle, payload)

    def test_group_alias_cannot_cross_splits_between_experiments(self):
        from corpus_check import validate_isolation
        rows = [{"case_id": "A", "version": 1, "control": {"source_group_id": "same", "split": "dev", "synthetic": True}},
                {"case_id": "B", "version": 1, "control": {"source_group_id": "same", "split": "holdout", "synthetic": True}}]
        with self.assertRaisesRegex(ValueError, "source_group_split_overlap"):
            validate_isolation(rows)

    def test_nonsynthetic_or_duplicate_identity_rejected(self):
        from corpus_check import validate_isolation
        row = {"case_id": "A", "version": 1, "control": {"source_group_id": "one", "split": "dev", "synthetic": True}}
        with self.assertRaisesRegex(ValueError, "case_identity_invalid"):
            validate_isolation([row, row])
        row["control"]["synthetic"] = False
        with self.assertRaisesRegex(ValueError, "synthetic_required"):
            validate_isolation([row])

