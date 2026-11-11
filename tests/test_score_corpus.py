"""Independent inventory and mutation checks for synthetic score drafts."""
from __future__ import annotations

import copy
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
DEVON = Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon"))


class ScoreCorpus(unittest.TestCase):
    def builder(self):
        path = LAB / "tools/build_score_corpus.py"
        self.assertTrue(path.is_file(), "Synthetic score corpus builder is missing")
        return importlib.import_module("tools.build_score_corpus")

    def build(self, directory):
        builder = self.builder()
        destination = Path(directory) / "answer"
        builder.build_corpus(destination, DEVON)
        return builder, destination

    def test_inventory_scopes_and_original_semantic_checks(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            observed = builder.validate_corpus(root, DEVON)
            self.assertEqual(observed["interviews"], 17)
            self.assertEqual(observed["turns"], 153)
            self.assertEqual(observed["main_pairs"], 255)
            self.assertEqual(observed["legacy_pairs"], 60)
            self.assertEqual(observed["numeric_pairs"], 289)
            self.assertEqual(observed["na_pairs"], 26)
            self.assertEqual(observed["na_turns"], 14)
            self.assertEqual(observed["split_counts"], {"dev": 13, "holdout": 4})
            self.assertEqual(observed["null_answers"], [["b-main-02", 1], ["b-main-06", 2]])
            self.assertEqual(observed["model_calls"], 0)
            for key in ("contribution_clarity", "project_understanding", "problem_solving", "company_job_fit"):
                self.assertEqual(observed["main_numeric_coverage"][key], {str(n): 3 for n in range(5)})
            self.assertEqual(observed["main_numeric_coverage"]["technical_reasoning"], {str(n): 12 for n in range(5)})
            self.assertEqual(observed["c8_coverage"], {str(n): 3 for n in range(5)})

    def test_null_answers_are_numeric_zero_without_cross_turn_imputation(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            _, root = self.build(directory)
            for case_id, turn_id in (("b-main-02", "1"), ("b-main-06", "2")):
                gold = json.loads((root / "main-v1/gold" / f"{case_id}.json").read_text(encoding="utf-8"))
                self.assertEqual([row["level"] for row in gold if row["turn_id"] == turn_id], [0, 0])

    def test_rubric_extraction_is_literal_and_never_imports_seed(self):
        builder = self.builder()
        rubrics, provenance = builder.extract_rubrics(DEVON / "backend/scripts/seed_score_criteria.py")
        self.assertEqual(sum(map(len, rubrics.values())), 30)
        self.assertEqual(rubrics["technical_reasoning"]["2"], "근거는 제시하나 대안과의 비교가 없거나 피상적이다.")
        self.assertEqual(len(provenance["source_sha256"]), 64)
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            path = Path(directory) / "seed.py"
            path.write_text("raise AssertionError('must not import')\nSCORE_CRITERIA = (ScoreCriterionSpec(score_key='x', rubric={'0': 'literal'}),)\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rubric_inventory_invalid"):
                builder.extract_rubrics(path)

    def test_no_overwrite_leaves_existing_bytes_intact(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/inputs/b-main-01.v1.json"
            before = path.read_bytes()
            with self.assertRaisesRegex(FileExistsError, "corpus_exists"):
                builder.build_corpus(root, DEVON)
            self.assertEqual(path.read_bytes(), before)

    def test_rejects_source_group_cross_split_even_before_filtering(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/inputs/b-main-09.v1.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["control"]["source_group_id"] = "sg-b-main-01"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_group_split_overlap"):
                builder.validate_corpus(root, DEVON)

    def test_rejects_label_leak_in_preanswer_contract(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/inputs/b-main-01.v1.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["payload"]["service_input"]["turns"][0]["question_contract"]["target_level"] = 4
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "contract_fields_invalid"):
                builder.validate_corpus(root, DEVON)

    def test_rejects_unknown_jd_and_wrong_rubric_quote(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/inputs/b-main-01.v1.json"
            original = path.read_text(encoding="utf-8")
            value = json.loads(original)
            value["payload"]["service_input"]["turns"][4]["jd_requirement_ids"] = ["unregistered"]
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "original_input_invalid"):
                builder.validate_corpus(root, DEVON)
            path.write_text(original, encoding="utf-8")
            gold_path = root / "main-v1/gold/b-main-01.json"
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            gold[0]["rubric_quote"] = "fabricated rubric wording"
            gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rubric_quote_invalid"):
                builder.validate_corpus(root, DEVON)

    def test_scope_not_jd_presence_controls_legacy_na(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            _, root = self.build(directory)
            for number in (1, 2):
                case_id = f"b-legacy-na-{number:02}"
                envelope = json.loads((root / "legacy-na-v1/inputs" / f"{case_id}.v1.json").read_text(encoding="utf-8"))
                turns = envelope["payload"]["service_input"]["turns"]
                self.assertTrue(all(turn["question_contract"]["evaluation_keys"] == [] for turn in turns))
                self.assertTrue(turns[7]["jd_requirement_ids"])
                gold = json.loads((root / "legacy-na-v1/gold" / f"{case_id}.json").read_text(encoding="utf-8"))
                f8 = next(row for row in gold if (row["turn_id"], row["key"]) == ("8", "company_job_fit"))
                self.assertEqual(f8["level"], "not_applicable")
                self.assertNotIn("rubric_quote", f8)

    def test_rejects_changed_preanswer_contract_and_catalogue_provenance(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/inputs/b-main-01.v1.json"
            original = path.read_text(encoding="utf-8")
            value = json.loads(original)
            value["payload"]["service_input"]["turns"][0]["question_contract"]["purpose"] += " changed after annotation"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preanswer_contract_changed"):
                builder.validate_corpus(root, DEVON)
            path.write_text(original, encoding="utf-8")
            catalogue_path = root / "main-v1/catalogue.json"
            catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
            catalogue["rubric_provenance"]["source_sha256"] = "0" * 64
            catalogue_path.write_text(json.dumps(catalogue, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rubric_provenance_invalid"):
                builder.validate_corpus(root, DEVON)

    def test_tool_error_does_not_remove_a_substantive_reasoned_answer(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            _, root = self.build(directory)
            envelope = json.loads((root / "main-v1/inputs/b-main-08.v1.json").read_text(encoding="utf-8"))
            gold = json.loads((root / "main-v1/gold/b-main-08.json").read_text(encoding="utf-8"))
            observations = envelope["payload"]["service_input"]["tool_results"]
            failed_turns = {row["turn_id"] for row in observations if row["result"]["status"] == "tool_error"}
            self.assertTrue(any(row["turn_id"] in failed_turns and row["key"] == "technical_reasoning" and row["level"] == 4 for row in gold))

    def test_rejects_source_bundle_alias_even_with_distinct_group_ids(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            path = root / "main-v1/catalogue.json"
            catalogue = json.loads(path.read_text(encoding="utf-8"))
            catalogue["cases"][8]["source_bundle_sha256"] = catalogue["cases"][0]["source_bundle_sha256"]
            path.write_text(json.dumps(catalogue, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_bundle_split_overlap"):
                builder.validate_corpus(root, DEVON)

    def test_rejects_catalogue_identity_split_and_answer_drift(self):
        with tempfile.TemporaryDirectory(dir=LAB / "runs") as directory:
            builder, root = self.build(directory)
            catalogue_path = root / "main-v1/catalogue.json"
            catalogue_original = catalogue_path.read_text(encoding="utf-8")
            for field, wrong in (("case_id", "b-main-99"), ("split", "holdout"), ("source_group_id", "other-group")):
                catalogue = json.loads(catalogue_original)
                catalogue["cases"][0][field] = wrong
                catalogue_path.write_text(json.dumps(catalogue, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "catalogue_identity_invalid"):
                    builder.validate_corpus(root, DEVON)
            catalogue_path.write_text(catalogue_original, encoding="utf-8")
            path = root / "main-v1/inputs/b-main-01.v1.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["payload"]["service_input"]["turns"][0]["answer"] += " changed after annotation"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "answer_draft_changed"):
                builder.validate_corpus(root, DEVON)


if __name__ == "__main__":
    unittest.main()

