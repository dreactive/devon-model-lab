"""Offline validation of the approved stage-2 synthetic drafts; no network client."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import asyncio
from collections import Counter
from pathlib import Path
import json
import hashlib

from jsonschema import Draft202012Validator

from lab_paths import attach_devon
from score_eval import read_json, load_inputs, load_manifest, validate_case

LAB_ROOT = Path(__file__).resolve().parent


def validate_isolation(envelopes: list[dict]) -> dict:
    groups, identities = {}, set()
    for envelope in envelopes:
        identity = envelope["case_id"], envelope["version"]
        if identity in identities:
            raise ValueError("case_identity_invalid")
        identities.add(identity)
        control = envelope["control"]
        if control.get("synthetic") is not True:
            raise ValueError("synthetic_required")
        group, split = control["source_group_id"], control["split"]
        if split not in {"dev", "holdout"} or not group:
            raise ValueError("split_invalid")
        if group in groups and groups[group] != split:
            raise ValueError("source_group_split_overlap")
        groups[group] = split
    return {"case_count": len(identities), "source_groups": len(groups),
            "split_counts": dict(Counter(item["control"]["split"] for item in envelopes))}


def _write(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def validate_bundle_binding(bundle: dict, service_input: dict) -> None:
    """Bind authoring source claims to the exact source texts used in this corpus."""
    files = {item["path"]: item["content"] for item in bundle["files"]}
    if len(files) != len(bundle["files"]):
        raise ValueError("source_bundle_binding_mismatch")
    identity = bundle["repository_id"], bundle["git_ref"]
    context = service_input["context"]
    if {(item["repository_id"], item["git_ref"]) for item in context["repositories"]} != {identity}:
        raise ValueError("source_bundle_binding_mismatch")
    evidence = list(context["evidence"])
    for result in service_input.get("tool_results", []):
        evidence.extend(result["items"])
    supplied = set()
    for item in evidence:
        if (item["source_kind"] not in {"code", "document"}
                or (item["repository_id"], item["git_ref"]) != identity
                or item["path"] not in files or item["content"] != files[item["path"]]):
            raise ValueError("source_bundle_binding_mismatch")
        supplied.add(item["path"])
    # The approved corpus uses its complete authored excerpts and no separate text override.
    if supplied != set(files) or service_input.get("reference_texts", []):
        raise ValueError("source_bundle_binding_mismatch")


def validate_question_drafts(root: Path, cases, catalogue: list[dict], *, expected_controls: int = 105,
                             expected_decisions: int = 4) -> dict:
    """Replay actual stored authoring contracts and calibration shapes, without a Judge."""
    from devon_ai import contracts as c
    from scripts.ai_eval_bridge import prepare
    from app.features.interview.agent_context import allowed_personas
    from app.features.interview.evaluation_coverage import plan_evaluation_targets
    from devon_ai.agents.director.agent import _references
    from devon_ai.agents.director.runtime import _bounded_plan_schema, _validate_candidate, verification_decision
    index = {row["case_id"]: row for row in catalogue}
    controls, decisions, hashes = 0, {}, {}
    for case in cases:
        row = index[case.case_id]
        authoring = read_json(root / row["authoring_input"])
        _, data = prepare(case.kind, case.model_input())
        context = data["context"]
        counts = {persona: sum(turn.persona == persona for turn in context.history)
                  for persona in ("tech_lead", "hr_manager", "domain_lead")}
        allowed = allowed_personas(counts, turn_no=context.turn_no,
            quota={"tech_lead": 6, "hr_manager": 1, "domain_lead": 2})
        history = authoring["history_contracts"]
        contracts = tuple(c.decode_strict(c.QuestionContract, item["question_contract"]) for item in history)
        if (len(contracts) != len(context.history) or context.turn_no != len(context.history) + 1
            or context.allowed_personas != allowed or context.evaluation_targets != plan_evaluation_targets(
                contracts, allowed, has_jd=bool(context.jd_requirements))
            or any(turn.turn_id != item["turn_id"] or item["authored_before_answer"] is not True
                   for turn, item in zip(context.history, history, strict=True))):
            raise ValueError("question_state_replay_failed:" + case.case_id)
        if context.history and context.current_question_contract != contracts[-1]:
            raise ValueError("question_current_contract_mismatch")
        bundle = authoring["synthetic_source_bundle"]
        if bundle["synthetic"] is not True or bundle["source_group_id"] != case.source_group_id:
            raise ValueError("source_bundle_invalid")
        validate_bundle_binding(bundle, case.payload["service_input"])
        for source in bundle["files"]:
            digest = hashlib.sha256(source["content"].encode("utf-8")).hexdigest()
            if digest != source["sha256"]:
                raise ValueError("source_hash_invalid")
            if digest in hashes and hashes[digest] != case.split:
                raise ValueError("source_text_split_overlap")
            hashes[digest] = case.split
        if authoring["review"]["status"] != "unreviewed":
            raise ValueError("draft_review_state_invalid")
        expected = row["verification_expected"]
        if expected is not None:
            decision = verification_decision(context, data["answer_analysis"], allowed_locations=data["allowed_locations"])
            actual = "skip" if isinstance(decision, str) else decision.data.next_step
            if actual != expected:
                raise ValueError("verification_subcheck_failed")
            decisions[case.case_id] = actual
        sources = _references(context, data["reference_texts"])
        schema = _bounded_plan_schema(context, sources, True)
        Draft202012Validator.check_schema(schema)
        calibrations = case.expectation["grader_controls"]
        if Counter(item["kind"] for item in calibrations) != {"allowed": 1, "forbidden": 1, "ambiguous": 1}:
            raise ValueError("calibration_coverage_invalid")
        for control in calibrations:
            output = json.loads(control["output"])
            question = c.decode_strict(c.Question, output["question"])
            _validate_candidate(question, context, sources, True)
            Draft202012Validator(schema).validate({"question": output["question"], "intent": "offline validation", "reason_summary": "offline validation"})
            checked = c.validate_question(question,
                review=c.QuestionReview(question.text, question.question_contract), allowed_personas=allowed,
                evidence_refs=frozenset(ref.id for ref in sources if ref.kind == "evidence"),
                basis_refs=frozenset(sources), jd_requirement_ids=frozenset(item.id for item in context.jd_requirements))
            c.validate_decision(c.decode_strict(c.DirectorDecision, output["decision"]), question=checked,
                allowed_personas=allowed, finish_allowed=False, allowed_locations=data["allowed_locations"])
            controls += 1
    if controls != expected_controls or len(decisions) != expected_decisions:
        raise ValueError("a_subcheck_count_invalid")
    return {"controls": controls, "control_validation": "schema_and_reference_only",
            "semantic_calibration": "not_run", "state_replays": len(cases),
            "verification_decisions": decisions, "unique_source_texts": len(hashes)}


async def run(devon_root: Path, output: Path, *, lab_root: Path = LAB_ROOT) -> dict:
    devon = attach_devon(devon_root)
    lab = lab_root.resolve()
    output = output.resolve()
    if output.is_relative_to(devon) or not output.is_relative_to(lab / "runs") or output.exists():
        raise ValueError("output_rejected")
    from scripts import run_ai_evaluation as engine
    from scripts.ai_eval_bridge import prepare
    from eval_cases import load_cases
    from question_runtime import (catalogue_rows, inspect_recovery,
        capture_director_request, capture_recovery_judge_request)
    from devon_ai import contracts as c
    from judge_context import validate_judge_context
    from run_lab import dry_run_question
    from execution_policy import build_plan, plan_digest
    from tools.build_score_corpus import validate_corpus

    question_root = lab / "cases/question/benchmark-v1"
    b_roots = [lab / "cases/answer/main-v1", lab / "cases/answer/legacy-na-v1"]
    manifest = lab / "manifests/baseline.json"
    catalogue = catalogue_rows(question_root)
    a_envelopes = [read_json(path) for path in sorted((question_root / "inputs").glob("*.json"))]
    b_cases = [(root, case) for root in b_roots for case in load_inputs(root)]
    isolation = validate_isolation(a_envelopes + [case.envelope for _, case in b_cases])
    if len(a_envelopes) != 35 or len(b_cases) != 17 or len(catalogue) != 35:
        raise ValueError("approved_corpus_count_mismatch")
    loaded = load_cases(question_root)
    if len(loaded) != 35 or any(case.expectation["review"]["status"] != "unreviewed" for case in loaded):
        raise ValueError("draft_review_state_invalid")
    a_drafts = validate_question_drafts(question_root, loaded, catalogue)
    b_drafts = validate_corpus(lab / "cases/answer", devon)
    prompts, limits, metadata = engine.load_manifest(manifest)
    judge_prompt = c.PromptSpec("evaluation_judge", "evaluation_judge_v3", "offline-capture-only",
        (devon / "ai/prompts/evaluation-judge-v3.md").read_text(encoding="utf-8"))
    # The original runner validates and loads separate expectations; no grader is enabled.
    a_result = await dry_run_question({"cases_path": str(question_root), "manifest_path": str(manifest), "split": "all"})
    if len(a_result.get("cases", [])) != 35 or any(row["status"] != "validated_only" for row in a_result["cases"]):
        raise ValueError("a_dry_run_rejected")
    a_requests, recovery = [], []
    for envelope in a_envelopes:
        prepare("question", envelope["payload"])
        component = inspect_recovery(question_root, envelope["case_id"], envelope["version"])
        captured = await capture_director_request(envelope["payload"], prompts, limits,
            task_limits=metadata.get("task_limits", {}), feedback=None if component is None else component.feedback)
        a_requests.append({"case_id": envelope["case_id"], **captured})
        if component is not None:
            validate_judge_context(component.source_context)
            judge_capture = await capture_recovery_judge_request(component, judge_prompt, limits)
            recovery.append({"case_id": envelope["case_id"], "sidecar_sha256": component.sidecar_sha256,
                "typed_feedback": True, "original_director_request": True,
                "judge_projection": "original_validator_passed", "judge_request_capture": judge_capture})
    if len(recovery) != 3:
        raise ValueError("recovery_count_mismatch")
    prompt, b_limits, b_metadata = load_manifest(manifest, devon)
    b_rows, levels, per_key, null_answers = [], Counter(), {}, 0
    for root, case in b_cases:
        row = await validate_case(case, root, prompt, b_limits)
        if row["status"] != "validated_only" or row["annotations"]["review_status"] != "unreviewed":
            raise ValueError("b_dry_run_rejected:" + case.envelope["case_id"] + ":" + str(row.get("error")))
        b_rows.append({"corpus": root.name, **row})
        null_answers += sum(turn.get("answer") is None for turn in case.envelope["payload"]["service_input"]["turns"])
        for item in read_json(root / "gold" / (case.envelope["case_id"] + ".json")):
            levels[str(item["level"])] += 1
            key_counts = per_key.setdefault(item["key"], Counter())
            key_counts[str(item["level"])] += 1
    if sum(levels.values()) != 315 or levels["not_applicable"] != 26 or null_answers != 2:
        raise ValueError("gold_coverage_mismatch")
    # No prices, dollar caps or real approvals are supplied: these plans must be blocked.
    plans = [build_plan(devon_root=devon, lab_root=lab, cases_path=root, manifest_path=manifest,
        pricing_path=lab / "pricing.yaml", experiment=experiment, split="all",
        base_url="https://offline-preparation.invalid/v1")
        for root, experiment in [(question_root, "A"), *[(root, "B") for root in b_roots]]]
    if any(not {"budget_missing", "http_attempt_cap_missing", "model_price_incomplete"} <= set(plan["blocked_reasons"]) for plan in plans):
        raise ValueError("unpriced_execution_not_blocked")
    result = {"status": "validated_only", "api_calls": 0, "provider_attempts": 0,
        "review_status": "unreviewed", "quality_evaluation": "not_run", "quality_denominator": 0,
        "annotation_correctness": "human_review_pending", "isolation": isolation,
        "A": {"cases": 35, "service_cases": 32, "recovery_components": recovery,
              "draft_checks": a_drafts,
              "split_counts": dict(Counter(item["control"]["split"] for item in a_envelopes)),
              "original_engine": a_result, "captured_requests": a_requests},
        "B": {"interviews": 17, "turns": sum(row["turn_count"] for row in b_rows),
              "draft_checks": b_drafts,
              "gold_pairs": sum(levels.values()), "numeric_pairs": sum(levels.values()) - levels["not_applicable"],
              "na_pairs": levels["not_applicable"], "null_answers": null_answers,
              "level_counts": dict(levels), "per_key_level_counts": {k: dict(v) for k, v in per_key.items()},
              "manifest": b_metadata, "cases": b_rows},
        "execution_plans": [{"corpus": plan["config"]["cases_path"],
             "blocked_reasons": plan["blocked_reasons"], "selected_cases": len(plan["selected_case_ids"]),
             "expected_cost": "미수집", "approved": False,
             "plan_sha256": plan_digest(plan), "plan": plan} for plan in plans]}
    output.parent.mkdir(parents=True, exist_ok=True)
    _write(output, result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--devon-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(run(args.devon_root, args.output))
        print(json.dumps({"status": result["status"], "A": 35, "B": 17, "gold_pairs": 315, "api_calls": 0}))
        return 0
    except Exception as error:
        print(json.dumps({"status": "failed", "code": str(error), "api_calls": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
