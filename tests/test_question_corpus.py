"""Offline checks for the authored A corpus, against original service contracts."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import UUID

sys.dont_write_bytecode = True
LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from lab_paths import attach_devon
attach_devon(Path(os.environ.get("DEVON_ROOT", "C:/Users/dreac/Desktop/kdt/devon")))


class QuestionCorpusTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("tools.build_question_corpus")

    def test_builder_exclusive_creation_preserves_existing_files(self):
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory) / "fresh"
            self.builder.build_corpus(root)
            original = (root / "catalogue.json").read_bytes()
            with self.assertRaises(FileExistsError):
                self.builder.build_corpus(root)
            self.assertEqual((root / "catalogue.json").read_bytes(), original)

    def test_all_cases_use_original_prepare_controller_and_dynamic_contracts(self):
        from eval_cases import load_cases
        from scripts.ai_eval_bridge import prepare
        from app.features.interview.agent_context import allowed_personas
        from app.features.interview.evaluation_coverage import plan_evaluation_targets
        from devon_ai import contracts as c
        from devon_ai.agents.director.agent import _references
        from devon_ai.agents.director.runtime import (
            _bounded_plan_schema, _input_payload, _validate_candidate, verification_decision,
        )
        import jsonschema
        with tempfile.TemporaryDirectory(dir=LAB / "tests") as directory:
            root = Path(directory) / "fresh"
            self.builder.build_corpus(root)
            cases = load_cases(root)
            catalogue = json.loads((root / "catalogue.json").read_text(encoding="utf-8"))
            self.assertEqual(len(cases), 35)
            self.assertEqual(Counter(case.split for case in cases), {"dev": 25, "holdout": 10})
            self.assertEqual(Counter(row["scope"] for row in catalogue["cases"]),
                             {"service": 32, "recovery_component": 3})
            self.assertEqual(Counter(row["category"] for row in catalogue["cases"]),
                             {"A1": 3, "A2": 4, "A3": 4, "A4": 3, "A5": 3,
                              "A6": 3, "A7": 4, "A8": 4, "A9": 4, "A10": 3})
            index = {row["case_id"]: row for row in catalogue["cases"]}
            subchecks = {}
            for case in cases:
                with self.subTest(case=case.case_id):
                    task, data = prepare(case.kind, case.model_input())
                    self.assertEqual(task, "director")
                    context = data["context"]
                    UUID(context.interview_id)
                    for repository in context.repositories:
                        UUID(repository.repository_id)
                    counts = {persona: sum(turn.persona == persona for turn in context.history)
                              for persona in ("tech_lead", "hr_manager", "domain_lead")}
                    self.assertEqual(context.allowed_personas, allowed_personas(
                        counts, turn_no=context.turn_no,
                        quota={"tech_lead": 6, "hr_manager": 1, "domain_lead": 2}))
                    self.assertEqual(context.turn_no, len(context.history) + 1)
                    self.assertEqual(context.limits.remaining_calls, 2)
                    self.assertEqual(context.limits.remaining_replans, 0)
                    row = index[case.case_id]
                    authoring = json.loads((root / row["authoring_input"]).read_text(encoding="utf-8"))
                    contracts = tuple(c.decode_strict(c.QuestionContract, item["question_contract"])
                                      for item in authoring["history_contracts"])
                    self.assertEqual(len(contracts), len(context.history))
                    self.assertEqual(context.evaluation_targets, plan_evaluation_targets(
                        contracts, context.allowed_personas, has_jd=bool(context.jd_requirements)))
                    for turn, contract_row in zip(context.history, authoring["history_contracts"], strict=True):
                        self.assertEqual(turn.turn_id, contract_row["turn_id"])
                        self.assertNotIn("question_contract", asdict(turn))
                    self.assertTrue(authoring["synthetic_source_bundle"]["synthetic"])
                    self.assertTrue(authoring["synthetic_source_bundle"]["files"])
                    if context.history:
                        self.assertTrue(context.jd_requirements)
                        self.assertEqual(context.current_question_contract, contracts[-1])
                    else:
                        self.assertNotIn("answer_analysis", case.payload["service_input"])
                    _input_payload(context, c.PromptSpec("director", "director_v8", "offline", "offline"),
                                   c.CallLimits(30, 2048, 500000, 500000),
                                   data.get("answer_analysis"), data["reference_texts"], None,
                                   data["tool_results"])
                    expected = row["verification_expected"]
                    if expected:
                        result = verification_decision(context, data["answer_analysis"],
                                                       allowed_locations=data["allowed_locations"])
                        subchecks[case.case_id] = "skip" if isinstance(result, str) else result.data.next_step
                        self.assertEqual(subchecks[case.case_id], expected)
                    sources = _references(context, data["reference_texts"])
                    schema = _bounded_plan_schema(context, sources, True)
                    controls = case.expectation["grader_controls"]
                    self.assertEqual(Counter(item["kind"] for item in controls),
                                     {"allowed": 1, "forbidden": 1, "ambiguous": 1})
                    self.assertGreaterEqual(len(case.expectation["allowed"]), 1)
                    self.assertGreaterEqual(len(case.expectation["forbidden"]), 1)
                    for forbidden in case.expectation["forbidden"]:
                        self.assertTrue(forbidden["type"])
                    self.assertEqual(case.expectation["review"]["status"], "unreviewed")
                    self.assertEqual(case.expectation["review"]["author"], "Codex")
                    self.assertIsNone(case.expectation["review"]["reviewer"])
                    self.assertIsNone(case.expectation["review"]["reviewed_at"])
                    for control in controls:
                        output = json.loads(control["output"])
                        question = c.decode_strict(c.Question, output["question"])
                        _validate_candidate(question, context, sources, True)
                        jsonschema.validate({"question": output["question"], "intent": "offline validation",
                                             "reason_summary": "offline validation"}, schema)
                        checked = c.validate_question(question,
                            review=c.QuestionReview(question.text, question.question_contract),
                            allowed_personas=context.allowed_personas,
                            evidence_refs=frozenset(ref.id for ref in sources if ref.kind == "evidence"),
                            basis_refs=frozenset(sources),
                            jd_requirement_ids=frozenset(item.id for item in context.jd_requirements))
                        c.validate_decision(c.decode_strict(c.DirectorDecision, output["decision"]),
                            question=checked, allowed_personas=context.allowed_personas,
                            finish_allowed=False, allowed_locations=data["allowed_locations"])
                    if row["category"] == "A8":
                        self.assertEqual(set(context.allowed_personas), {"tech_lead", "domain_lead"})
                    if row["scope"] == "recovery_component":
                        runtime = json.loads((root / row["runtime_input"]).read_text(encoding="utf-8"))
                        self.assertEqual(set(runtime), {"case_id", "version", "scope", "recovery_feedback"})
                        feedback = runtime["recovery_feedback"]
                        self.assertEqual(set(feedback), {"previous_candidate", "recovery"})
                        _validate_candidate(c.decode_strict(c.Question, feedback["previous_candidate"]),
                                            context, sources, True)
                        c.decode_strict(c.CandidateRecovery, feedback["recovery"])
            self.assertEqual(subchecks, {"a-dev-0004": "retrieve", "a-dev-0014": "skip",
                                        "a-dev-0023": "retrieve", "a-holdout-0004": "retrieve"})


if __name__ == "__main__":
    unittest.main()
