"""Strict, offline subset selection without changing any source cases."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

LAB = Path(__file__).resolve().parents[1]


class CaseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=LAB / "runs")
        self.addCleanup(self.temp.cleanup)
        self.lab = Path(self.temp.name)
        self.a = self.lab / "cases/question/benchmark-v1"
        self.b = self.lab / "cases/answer/main-v1"
        self.path = self.lab / "selections/dev-30pct-v1.json"
        self.document = {
            "version": 1, "selection_id": "dev-30pct-v1",
            "reference_population": {"A": 35, "B": 17, "total": 52},
            "split": "dev", "review_status": "unreviewed", "model_ids": ["fixture-model"],
            "datasets": [
                {"experiment": "A", "cases_root": "cases/question/benchmark-v1",
                 "cases": [{"case_id": "a-one", "version": 1}]},
                {"experiment": "B", "cases_root": "cases/answer/main-v1",
                 "cases": [{"case_id": "b-one", "version": 1}]},
            ],
        }
        self.source(self.a, "a-one", "question")
        self.source(self.a, "a-two", "question")
        self.source(self.b, "b-one", "report")
        self.source(self.b, "b-holdout", "report", split="holdout")
        self.write(self.path, self.document)

    def module(self):
        self.assertTrue((LAB / "case_selection.py").is_file(), "case selection module missing")
        return importlib.import_module("case_selection")

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def source(self, root, identifier, kind, *, split="dev"):
        value = {"case_id": identifier, "version": 1,
            "control": {"kind": kind, "split": split, "source_group_id": identifier, "synthetic": True},
            "payload": {"service_task": "fixture", "service_input": {"text": "untouched"}}}
        self.write(root / "inputs" / f"{identifier}.v1.json", value)

    def resolve(self, **changes):
        args = dict(lab_root=self.lab, cases_path=self.a, experiment="A", split="dev")
        args.update(changes)
        return self.module().resolve_selection(self.path, **args)

    def test_resolves_requested_subset_and_leaves_source_bytes_untouched(self):
        before = {path: path.read_bytes() for path in self.lab.rglob("*.json")}
        selected = self.resolve()
        self.assertEqual(selected.selection_id, "dev-30pct-v1")
        self.assertEqual(selected.case_keys, frozenset({("a-one", 1)}))
        self.assertEqual(selected.model_ids, ("fixture-model",))
        self.assertTrue(selected.matches("a-one", 1))
        self.assertFalse(selected.matches("a-one", 2))
        self.assertEqual(selected.fingerprint["path"], str(self.path.resolve()))
        self.assertEqual(selected.fingerprint["bytes"], self.path.stat().st_size)
        self.assertEqual(len(selected.fingerprint["sha256"]), 64)
        with self.assertRaises(FrozenInstanceError):
            selected.selection_id = "changed"
        self.assertEqual(before, {path: path.read_bytes() for path in self.lab.rglob("*.json")})

    def test_holdout_in_another_dataset_rejects_before_filtering(self):
        self.document["datasets"][1]["cases"] = [{"case_id": "b-holdout", "version": 1}]
        self.write(self.path, self.document)
        with self.assertRaisesRegex(ValueError, "selection_source_invalid"):
            self.resolve()

    def test_unknown_or_stale_version_rejects(self):
        for identity in ({"case_id": "missing", "version": 1}, {"case_id": "a-one", "version": 2}):
            with self.subTest(identity=identity):
                self.document["datasets"][0]["cases"] = [identity]
                self.write(self.path, self.document)
                with self.assertRaises(ValueError):
                    self.resolve()

    def test_duplicate_dataset_or_identity_rejects(self):
        self.document["datasets"].append(self.document["datasets"][0])
        self.write(self.path, self.document)
        with self.assertRaisesRegex(ValueError, "selection_document_invalid"):
            self.resolve()
        self.document["datasets"].pop()
        self.document["datasets"][0]["cases"].append({"case_id": "a-one", "version": 1})
        self.write(self.path, self.document)
        with self.assertRaisesRegex(ValueError, "selection_document_invalid"):
            self.resolve()

    def test_path_traversal_and_noncanonical_dataset_paths_reject(self):
        for relative in ("../elsewhere", "cases/../cases/question/benchmark-v1", "cases\\question\\benchmark-v1", "/cases/question", "./cases/question/benchmark-v1"):
            with self.subTest(relative=relative):
                self.document["datasets"][0]["cases_root"] = relative
                self.write(self.path, self.document)
                with self.assertRaisesRegex(ValueError, "selection_path_invalid"):
                    self.resolve()

    def test_document_must_live_in_lab_selections(self):
        outside = self.lab / "not-selections.json"
        self.write(outside, self.document)
        with self.assertRaisesRegex(ValueError, "selection_path_invalid"):
            self.module().resolve_selection(outside, lab_root=self.lab, cases_path=self.a, experiment="A", split="dev")

    def test_wrong_requested_split_experiment_or_root_rejects(self):
        for changes in ({"split": "all"}, {"split": "holdout"}, {"experiment": "B"}, {"cases_path": self.lab / "cases/question/missing"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.resolve(**changes)

    def test_boolean_versions_extra_labels_and_duplicate_models_reject(self):
        mutations = [
            lambda doc: doc.update(version=True),
            lambda doc: doc.update(gold="forbidden"),
            lambda doc: doc.update(review_status="approved"),
            lambda doc: doc.update(model_ids=["same", "same"]),
            lambda doc: doc["datasets"][0]["cases"][0].update(version=True),
            lambda doc: doc["datasets"][0]["cases"][0].update(expected=4),
            lambda doc: doc["reference_population"].update(total=38),
            lambda doc: doc["reference_population"].update(A=35.0),
            lambda doc: doc["datasets"][0].update(experiment=[]),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                value = json.loads(json.dumps(self.document))
                mutation(value)
                self.write(self.path, value)
                with self.assertRaisesRegex(ValueError, "selection_document_invalid"):
                    self.resolve()

    def test_source_identity_kind_and_synthetic_are_checked(self):
        source = self.a / "inputs/a-one.v1.json"
        initial = json.loads(source.read_text(encoding="utf-8"))
        for change in ({"case_id": "different"}, {"version": True}, {"control": {**initial["control"], "kind": "report"}}, {"control": {**initial["control"], "synthetic": False}}):
            with self.subTest(change=change):
                self.write(source, {**initial, **change})
                with self.assertRaisesRegex(ValueError, "selection_source_invalid"):
                    self.resolve()

    def test_duplicate_json_keys_are_not_accepted(self):
        raw = self.path.read_text(encoding="utf-8").replace('"version": 1,', '"version": 1, "version": 1,', 1)
        self.path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "selection_document_invalid"):
            self.resolve()

    def test_filter_preserves_original_objects_payloads_and_order(self):
        module, selection = self.module(), self.resolve()
        other = SimpleNamespace(case_id="a-two", version=1, payload={"text": "other"})
        selected = SimpleNamespace(case_id="a-one", version=1, payload={"text": "same"})
        result = module.filter_cases([other, selected], selection)
        self.assertEqual(result, [selected])
        self.assertIs(result[0], selected)
        self.assertEqual(selected.payload, {"text": "same"})
        enveloped = SimpleNamespace(envelope={"case_id": "a-one", "version": 1, "payload": {"text": "same"}})
        self.assertIs(module.filter_cases([enveloped], selection)[0], enveloped)

    def test_filter_missing_duplicate_and_version_mismatch_reject(self):
        module, selection = self.module(), self.resolve()
        selected = SimpleNamespace(case_id="a-one", version=1)
        for source in ([], [selected, selected], [SimpleNamespace(case_id="a-one", version=2)]):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "selection_cases_mismatch"):
                module.filter_cases(source, selection)

