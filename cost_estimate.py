"""Prepare an API-free expected cost range from real service request sizes."""

from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import yaml

from cost_accounting import estimate_cost, load_pricing
from lab_paths import attach_devon

LAB_ROOT = Path(__file__).resolve().parent


def _selected_cases(args, cases, model_id):
    if getattr(args, "selection_path", None) is None:
        return cases
    from case_selection import resolve_selection, filter_cases
    selection = resolve_selection(args.selection_path, lab_root=LAB_ROOT,
        cases_path=args.cases, experiment=args.experiment, split=args.split)
    if model_id not in selection.model_ids:
        raise ValueError("selection_model_mismatch")
    return filter_cases(cases, selection)


def requests(args: argparse.Namespace, devon: Path) -> tuple[str, object, list[dict]]:
    from devon_ai import contracts as c
    from app.integrations.llm.client import request_size
    from scripts.run_ai_evaluation import load_manifest

    prompts, limits, metadata = load_manifest(args.manifest)
    task = "director" if args.experiment == "A" else "report_score"
    limits = replace(limits, **metadata.get("task_limits", {}).get(task, {}))
    prompt = prompts[task]
    runtime = json.loads((devon / "ai/prompts/runtime-prompts.json").read_text(encoding="utf-8"))[task]
    expected_template = (devon / "ai/prompts" / runtime["template"]).read_text(encoding="utf-8-sig")
    if prompt.version != runtime["version"] or prompt.template != expected_template:
        raise ValueError("service_prompt_mismatch")
    rows = []
    if args.experiment == "A":
        from eval_cases import load_cases
        from scripts.ai_eval_bridge import prepare
        from devon_ai.agents.director.runtime import _bounded_plan_schema, _input_payload, _feedback_payload
        from question_runtime import inspect_recovery

        for case in _selected_cases(args, load_cases(args.cases), prompt.model):
            if args.split != "all" and case.split != args.split:
                continue
            if case.kind != "question":
                raise ValueError("question_only_estimate")
            _, data = prepare(case.kind, case.payload)
            payload, sources = _input_payload(
                data["context"], prompt, limits, data.get("answer_analysis"),
                data["reference_texts"], None, data["tool_results"],
            )
            if (args.cases / "catalogue.json").is_file():
                recovery = inspect_recovery(args.cases, case.case_id, case.version)
                if recovery is not None:
                    payload["recovery_feedback"] = _feedback_payload(recovery.feedback)
            schema = _bounded_plan_schema(data["context"], sources, bool(data["context"].evaluation_targets))
            rows.append((case.case_id, {**payload, "operation": "plan"}, schema, "DirectorPlan", "director-plan.v3"))
    else:
        import score_eval
        from devon_ai.llm_tasks import report, report_score

        for case in _selected_cases(args, score_eval.load_inputs(args.cases), prompt.model):
            envelope = case.envelope
            if args.split != "all" and envelope["control"]["split"] != args.split:
                continue
            turns, rubric, report_input = report._build_inputs(envelope["payload"]["service_input"])
            report_score.check_input(turns, rubric)
            c.validate_report_input(report_input)
            c.validate_supplemental_input(report_input.supplemental_sources,
                contracts=tuple(turn.question_contract for turn in turns), limitations=report_input.limitations)
            payload = report_score._payload(
                turns, rubric, report_input.supplemental_sources, report_input.limitations,
                report_input.evidence, report_input.tool_results, report_input.source_notes, scoped=True,
            )
            rows.append((envelope["case_id"], payload, report_score._output_schema(), "ScoreJudgments", "1"))
    measured = []
    for case_id, payload, schema, name, version in rows:
        request = c.ModelRequest(prompt, payload, name, version, schema, limits, max_attempts=1)
        byte_count = request_size(request)
        if byte_count > limits.max_input_bytes:
            raise ValueError("input_budget_exceeded")
        character_count = len(prompt.template) + len(json.dumps(payload, ensure_ascii=False)) + len(json.dumps(schema, ensure_ascii=False))
        measured.append({"case_id": case_id, "payload_and_prompt_schema_characters": character_count,
                         "serialized_request_bytes": byte_count,
                         "request_sha256": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
    if not measured:
        raise ValueError("no_cases_selected")
    return prompt.model, limits, measured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--experiment", choices=("A", "B"), required=True)
    parser.add_argument("--devon-root", type=Path)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=LAB_ROOT / "manifests/baseline.json")
    parser.add_argument("--pricing", type=Path, default=LAB_ROOT / "pricing.yaml")
    parser.add_argument("--split", choices=("all", "dev", "holdout"), default="dev")
    parser.add_argument("--selection", dest="selection_path", type=Path)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-model-attempts", type=int)
    parser.add_argument("--max-judge-attempts", type=int, default=0)
    parser.add_argument("--budget-usd", type=Decimal)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        devon = attach_devon(args.devon_root)
        if args.output.resolve().is_relative_to(devon) or args.output.exists():
            raise ValueError("output_rejected")
        if args.repeats < 1 or args.max_judge_attempts < 0:
            raise ValueError("invalid_attempt_limit")
        if args.experiment == "B" and args.max_judge_attempts:
            raise ValueError("score_experiment_has_no_judge")
        if args.budget_usd is not None and (not args.budget_usd.is_finite() or args.budget_usd <= 0):
            raise ValueError("invalid_budget")
        model, limits, measured = requests(args, devon)
        nominal_calls = len(measured) * args.repeats * (2 if args.experiment == "A" else 1)
        max_calls = args.max_model_attempts if args.max_model_attempts is not None else len(measured) * args.repeats * 2
        if max_calls < nominal_calls:
            raise ValueError("attempt_cap_below_nominal_completion")
        pricing = load_pricing(args.pricing)
        mean_characters = sum(item["payload_and_prompt_schema_characters"] for item in measured) / len(measured)
        estimated_input = max(1, math.ceil(mean_characters / 4))
        service = estimate_cost(model, input_tokens_lower=estimated_input,
            input_tokens_upper=limits.max_input_bytes, output_tokens_upper=limits.max_output_tokens,
            calls_lower=nominal_calls, calls_upper=max_calls, pricing=pricing)
        groups = [{"role": "service", "model": model, "estimate": service}]
        if args.max_judge_attempts:
            config = yaml.safe_load((LAB_ROOT / "models.yaml").read_text(encoding="utf-8"))
            judge_model = config["judge"].get("model_id") or "unconfigured_judge"
            groups.append({"role": "judge_including_controls", "model": judge_model,
                "estimate": estimate_cost(judge_model, input_tokens_lower=1,
                    input_tokens_upper=limits.max_input_bytes, output_tokens_upper=limits.max_output_tokens,
                    calls_lower=0, calls_upper=args.max_judge_attempts, pricing=pricing)})
        lower = [group["estimate"].get("expected_lower_usd") for group in groups]
        upper = [group["estimate"].get("expected_upper_usd") for group in groups]
        total_lower = str(sum((Decimal(value) for value in lower), Decimal(0))) if all(value is not None for value in lower) else None
        total_upper = str(sum((Decimal(value) for value in upper), Decimal(0))) if all(value is not None for value in upper) else None
        report = {
            "mode": "estimate", "label": "예상 — 실제 사용량 아님", "experiment": args.experiment,
            "model_calls": 0, "nominal_service_calls": nominal_calls, "max_model_attempts": max_calls,
            "max_judge_attempts": args.max_judge_attempts, "max_total_http_attempts": max_calls + args.max_judge_attempts,
            "estimated_lower_usd": total_lower, "estimated_upper_usd": total_upper,
            "status": "estimated" if total_upper is not None else "not_collected", "groups": groups,
            "input_measurements": measured, "repeats": args.repeats,
            "assumptions": [
                "Input lower estimate uses measured prompt+schema+payload characters / 4; this is a heuristic, not a guaranteed token lower bound.",
                "Input upper estimate uses max_input_bytes as a conservative token allowance for every request, including unknown generated review text.",
                "Output lower allowance is 0; upper is max_output_tokens per attempt. No cached discount or omitted reasoning usage is assumed.",
                "Judge cap must include candidate judgments and control calibration. Prices and approval must be supplied separately.",
                "An HTTP attempt can incur cost before usage is known; an estimate is not a provider billing guarantee.",
            ],
            "max_budget_usd": str(args.budget_usd) if args.budget_usd is not None else None,
            "estimated_upper_exceeds_budget": Decimal(total_upper) > args.budget_usd if total_upper is not None and args.budget_usd is not None else None,
            "approval_required": True, "approved": False, "execution_enabled": False,
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "pricing_sha256": hashlib.sha256(args.pricing.read_bytes()).hexdigest(),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except Exception:
        print(json.dumps({"status": "failed", "error": "cost_estimate_rejected", "model_calls": 0}))
        return 1
    print(json.dumps({key: report[key] for key in ["label", "status", "max_total_http_attempts",
          "estimated_lower_usd", "estimated_upper_usd", "approval_required", "execution_enabled", "model_calls"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
