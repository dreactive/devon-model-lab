"""Fictional offline approval tests for fixed, versioned case selections."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import test_execution_policy as fixtures
from execution_policy import PolicyError, build_plan


class SelectionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExecutionPolicyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.kwargs = dict(self.fixture.kwargs)
        self.lab = self.fixture.lab
        self.cases = self.fixture.cases
        for case_id, split in (("one", "dev"), ("two", "dev"), ("held", "holdout")):
            self.fixture.write(self.cases / "inputs" / f"{case_id}.v1.json", {
                "case_id": case_id, "version": 1,
                "control": {"kind": "question", "split": split,
                            "synthetic": True, "source_group_id": case_id}, "payload": {}})
        self.selection_path = self.lab / "selections/dev-selection.json"
        self.selection = {"version": 1, "selection_id": "fictional-dev-selection",
            "reference_population": {"A": 35, "B": 17, "total": 52},
            "split": "dev", "model_ids": ["fictional-model"],
            "datasets": [{"experiment": "A", "cases_root": "cases/question",
                          "cases": [{"case_id": "one", "version": 1}]}],
            "review_status": "unreviewed"}
        self.fixture.write(self.selection_path, self.selection)

    def plan(self):
        return build_plan(**self.kwargs, selection_path=self.selection_path)

    def test_default_plan_keeps_all_dev_cases_and_no_selection_fields(self):
        plan = build_plan(**self.kwargs)
        self.assertEqual(plan["selected_case_ids"], ["one", "two"])
        self.assertNotIn("selection_path", plan["config"])
        self.assertNotIn("selection_document", plan["fingerprints"])

    def test_selected_plan_filters_ids_but_fingerprints_the_complete_root(self):
        plan = self.plan()
        self.assertEqual(plan["selected_case_ids"], ["one"])
        self.assertEqual(plan["config"]["selection_path"], str(self.selection_path.resolve()))
        self.assertEqual(plan["fingerprints"]["selection_document"]["path"], str(self.selection_path.resolve()))
        fingerprint_paths = {row["path"] for row in plan["fingerprints"]["cases"]}
        self.assertIn("inputs/two.v1.json", fingerprint_paths)
        self.assertIn("inputs/held.v1.json", fingerprint_paths)
        self.fixture.approve(plan)
        self.assertEqual(self.fixture.validate(plan).plan["selected_case_ids"], ["one"])

    def test_selection_change_invalidates_existing_approval(self):
        plan = self.plan()
        self.fixture.approve(plan)
        self.selection["selection_id"] = "changed-but-same-cases"
        self.fixture.write(self.selection_path, self.selection)
        with self.assertRaises(PolicyError):
            self.fixture.validate(plan)

    def test_excluded_annotation_change_also_invalidates_approval(self):
        annotation = self.cases / "expectations/two.v1.json"
        self.fixture.write(annotation, {"review": {"status": "unreviewed"}})
        plan = self.plan()
        self.fixture.approve(plan)
        annotation.write_bytes(annotation.read_bytes() + b"\n")
        with self.assertRaises(PolicyError):
            self.fixture.validate(plan)

    def test_models_outside_the_fixed_selection_are_rejected(self):
        self.selection["model_ids"] = ["other-fictional-model"]
        self.fixture.write(self.selection_path, self.selection)
        with self.assertRaisesRegex(PolicyError, "selection_model_mismatch"):
            self.plan()

    def test_unknown_holdout_and_wrong_versions_fail_before_plan(self):
        for case_id, version in (("unknown", 1), ("held", 1), ("one", 2)):
            with self.subTest(case_id=case_id, version=version):
                self.selection["datasets"][0]["cases"] = [{"case_id": case_id, "version": version}]
                self.fixture.write(self.selection_path, self.selection)
                with self.assertRaises(PolicyError):
                    self.plan()

    def test_selection_cannot_expand_to_all_or_holdout_split(self):
        for split in ("all", "holdout"):
            with self.subTest(split=split), self.assertRaises(PolicyError):
                build_plan(**(self.kwargs | {"split": split}), selection_path=self.selection_path)


if __name__ == "__main__":
    unittest.main()
