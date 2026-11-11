"""Validate report-score cases offline through DEVON's original request builder.

This entry point has no provider-execution flag. Gold is a separate annotation
contract: it is never a model response, never passed to a service validator, and
never added to the service input or captured request.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import asyncio
from dataclasses import asdict, dataclass, fields, replace
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from adapters.responses import ResponsesAdapter
from lab_paths import attach_devon

LAB_ROOT = Path(__file__).resolve().parent
FORBIDDEN_REQUEST_KEYS = frozenset({
    "gold", "expected", "expectation", "expectations", "review", "control",
    "acceptable", "rationale", "rubric_quote", "synthetic", "source_group_id", "split",
})


class LabError(ValueError):
    """Fixed, non-sensitive failure codes are the only exported error details."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LabError("json_invalid")
        result[key] = value
    return result


def _constant(_: str) -> object:
    raise LabError("json_invalid")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_object, parse_constant=_constant)
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise LabError("json_invalid") from None


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _schema_check(value: object, schema_name: str, error_code: str) -> None:
    try:
        schema = read_json(LAB_ROOT / "schemas" / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except (LabError, ValidationError, SchemaError, TypeError, ValueError, RecursionError):
        raise LabError(error_code) from None


def load_manifest(path: Path, devon_root: Path) -> tuple[Any, Any, dict[str, Any]]:
    """Use the original CLI manifest contract without importing its Settings path."""
    from devon_ai import contracts as c

    try:
        raw = read_json(path)
        if (type(raw) is not dict or not {"prompts", "limits"} <= set(raw)
                <= {"prompts", "limits", "task_limits"} or type(raw["prompts"]) is not list
                or type(raw["limits"]) is not dict):
            raise LabError("manifest_invalid")
        prompts: dict[str, Any] = {}
        for item in raw["prompts"]:
            if type(item) is not dict or set(item) != {
                "task_name", "version", "model", "template_path"
            } or any(type(value) is not str or not value.strip() for value in item.values()):
                raise LabError("manifest_invalid")
            template_path = (path.parent / item["template_path"]).resolve()
            prompt = c.PromptSpec(item["task_name"], item["version"], item["model"],
                                  template_path.read_text(encoding="utf-8-sig"))
            if prompt.task_name in prompts:
                raise LabError("manifest_invalid")
            prompts[prompt.task_name] = prompt
        limits = c.CallLimits(**raw["limits"])
        overrides = raw.get("task_limits", {})
        allowed = {item.name for item in fields(c.CallLimits)}
        if type(overrides) is not dict:
            raise LabError("manifest_invalid")
        for task, values in overrides.items():
            if (type(task) is not str or not task.strip() or type(values) is not dict
                    or set(values) - allowed):
                raise LabError("manifest_invalid")
            replace(limits, **values)
        prompt = prompts["report_score"]
        runtime = read_json(devon_root / "ai/prompts/runtime-prompts.json")["report_score"]
        original = (devon_root / "ai/prompts" / runtime["template"]).read_text(encoding="utf-8-sig")
        if prompt.version != runtime["version"] or prompt.template != original:
            raise LabError("service_prompt_mismatch")
        selected_limits = replace(limits, **overrides.get("report_score", {}))
        metadata = {
            "task_name": "report_score", "version": prompt.version, "model": prompt.model,
            "template_sha256": hashlib.sha256(prompt.template.encode("utf-8")).hexdigest(),
            "limits": asdict(selected_limits),
        }
        return prompt, selected_limits, metadata
    except LabError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        raise LabError("manifest_invalid") from None


@dataclass(frozen=True)
class CaseInput:
    path: Path
    envelope: dict[str, Any]


def load_inputs(root: Path) -> list[CaseInput]:
    """Check every split before filtering so source groups cannot cross splits."""
    found: list[CaseInput] = []
    identities: set[tuple[str, int]] = set()
    groups: dict[str, str] = {}
    inputs = root / "inputs"
    if not inputs.is_dir():
        raise LabError("cases_missing")
    for path in sorted(inputs.glob("*.json")):
        envelope = read_json(path)
        _schema_check(envelope, "report-input.schema.json", "input_contract_invalid")
        identity = (envelope["case_id"], envelope["version"])
        if identity in identities or path.name != f"{identity[0]}.v{identity[1]}.json":
            raise LabError("case_identity_invalid")
        identities.add(identity)
        control = envelope["control"]
        group, split = control["source_group_id"], control["split"]
        if group in groups and groups[group] != split:
            raise LabError("source_group_split_overlap")
        groups[group] = split
        found.append(CaseInput(path, envelope))
    if not found:
        raise LabError("cases_missing")
    return found


def validate_annotations(root: Path, envelope: dict[str, Any], turns: tuple[Any, ...],
                         rubric: tuple[Any, ...]) -> dict[str, Any]:
    """Check local annotation shape/consistency without judging human correctness."""
    from devon_ai import contracts as c

    case_id = envelope["case_id"]
    gold = read_json(root / "gold" / f"{case_id}.json")
    review = read_json(root / "reviews" / f"{case_id}.json")
    _schema_check(gold, "gold.schema.json", "annotation_contract_invalid")
    _schema_check(review, "review.schema.json", "annotation_contract_invalid")
    if review["case_id"] != case_id or review["version"] != envelope["version"]:
        raise LabError("annotation_contract_invalid")
    expected = {(turn.turn_id, key) for turn in turns for key in c.score_candidate_keys(turn)}
    pairs = [(item["turn_id"], item["key"]) for item in gold]
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise LabError("annotation_contract_invalid")
    unanswered = {turn.turn_id for turn in turns if turn.answer is None}
    rubric_text = {(item.key, item.level): item.text for item in rubric}
    for item in gold:
        acceptable = item.get("acceptable", [item["level"]])
        if item["level"] not in acceptable or len(acceptable) != len(set(acceptable)):
            raise LabError("annotation_contract_invalid")
        if item["turn_id"] in unanswered and any(level not in (0, "not_applicable") for level in acceptable):
            raise LabError("annotation_contract_invalid")
        quote = item.get("rubric_quote")
        if item["level"] == "not_applicable":
            # NA explains why the question's scope does not assess this candidate
            # key. It has no numeric rubric row to quote. Human rationale quality
            # remains unreviewed rather than being inferred by this local check.
            if "rubric_quote" in item:
                raise LabError("annotation_contract_invalid")
        elif type(quote) is not str or not quote.strip() or quote not in rubric_text.get((item["key"], item["level"]), ""):
            raise LabError("annotation_contract_invalid")
    return {"status": "contract_valid_only", "review_status": review["review"]["status"],
            "expected_pairs": len(expected), "human_correctness": "not_evaluated"}


def _reject_control_metadata(value: object) -> None:
    stack = [value]
    while stack:
        node = stack.pop()
        if type(node) is dict:
            if set(node) & FORBIDDEN_REQUEST_KEYS:
                raise LabError("request_control_metadata_rejected")
            stack.extend(node.values())
        elif type(node) is list:
            stack.extend(node)


class CaptureModelCall:
    """Injected ModelCall validates an original request and never calls its validator."""

    def __init__(self) -> None:
        self.requests: list[Any] = []
        self.metadata: dict[str, Any] | None = None
        self.adapter = ResponsesAdapter()

    async def __call__(self, request: Any, validator: Any) -> Any:
        from devon_ai import contracts as c
        from app.integrations.llm.client import request_size

        if type(request) is not c.ModelRequest or request.prompt.task_name != "report_score":
            raise LabError("request_contract_invalid")
        if self.requests or request.schema_name != "ScoreJudgments" or request.schema_version != "1":
            raise LabError("request_contract_invalid")
        _reject_control_metadata(request.payload)
        size = request_size(request)
        if size > request.limits.max_input_bytes:
            raise LabError("request_input_budget_exceeded")
        result = await self.adapter.call(request.prompt.model, request.prompt.template,
                                         request.payload, request.output_schema)
        if result.status != "dry_run" or result.model_calls != 0 or result.data is not None:
            raise LabError("offline_adapter_contract_invalid")
        self.requests.append(request)
        self.metadata = {
            "task_name": request.prompt.task_name, "schema_name": request.schema_name,
            "schema_version": request.schema_version, "payload_sha256": digest(request.payload),
            "output_schema_sha256": digest(request.output_schema), "input_bytes": size,
            "max_attempts": request.max_attempts, "status": "captured_only",
            "schema_enforced_by_provider": None,
        }
        # No fabricated judgment is supplied, and validator is deliberately unused.
        return c.ModelResult(None, c.CallFailure("budget", "dry_run", "Offline request captured."), ())


async def validate_case(case: CaseInput, root: Path, prompt: Any, limits: Any) -> dict[str, Any]:
    from devon_ai import contracts as c
    from devon_ai.llm_tasks import report, report_score

    envelope = case.envelope
    row: dict[str, Any] = {"case_id": envelope["case_id"], "version": envelope["version"],
                           "split": envelope["control"]["split"], "model_calls": 0}
    try:
        turns, rubric, report_input = report._build_inputs(envelope["payload"]["service_input"])
        report_score.check_input(turns, rubric)
        c.validate_report_input(report_input)
        c.validate_supplemental_input(
            report_input.supplemental_sources,
            contracts=tuple(turn.question_contract for turn in turns),
            limitations=report_input.limitations,
        )
        annotations = validate_annotations(root, envelope, turns, rubric)
        capture = CaptureModelCall()
        result = await report_score.judge_scores(
            turns, rubric=rubric, prompt=prompt, limits=limits, model_call=capture,
            supplemental_sources=report_input.supplemental_sources,
            limitations=report_input.limitations, evidence=report_input.evidence,
            tool_results=report_input.tool_results, source_notes=report_input.source_notes,
        )
        if (len(capture.requests) != 1 or result.data is not None or result.failure is None
                or result.failure.error_code != "dry_run" or result.attempts):
            raise LabError("service_precheck_rejected")
        row.update(status="validated_only", turn_count=len(turns), rubric_rows=len(rubric),
                   annotations=annotations, request=capture.metadata,
                   checks={"input_contract": "passed", "service_prechecks": "passed",
                           "request_contract": "passed", "annotation_contract": "passed"})
    except c.ContractError:
        row.update(status="rejected", error={"code": "service_input_invalid"})
    except LabError as error:
        row.update(status="rejected", error={"code": error.code})
    return row


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rejected = sum(row["status"] == "rejected" for row in rows)
    status = "rejected" if rejected else "validated_only" if rows else "not_run"
    return {"status": status, "validation_scope": "validated_only", "model_calls": 0, "total_cases": len(rows),
            "validated_cases": sum(row["status"] == "validated_only" for row in rows),
            "rejected_cases": rejected,
            "quality_evaluation": "not_run", "annotation_correctness": "not_evaluated"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Offline report_score input and request validation.",
                                     allow_abbrev=False)
    result.add_argument("--devon-root", type=Path)
    result.add_argument("--cases", type=Path, default=LAB_ROOT / "cases/answer")
    result.add_argument("--manifest", type=Path, default=LAB_ROOT / "manifests/baseline.json")
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--dry-run", action="store_true", default=True,
                        help="Offline validation; always enabled in stage 1.")
    result.add_argument("--split", choices=("all", "dev", "holdout"), default="dev")
    result.add_argument("--selection", dest="selection_path", type=Path)
    return result


async def run(args: argparse.Namespace) -> dict[str, Any]:
    devon_root = attach_devon(args.devon_root)
    if args.output.resolve().is_relative_to(devon_root):
        raise LabError("output_inside_devon_rejected")
    from scripts.evaluation_output import RunOutput

    output = RunOutput(args.output)
    report: dict[str, Any] = {"experiment": "B", "mode": "dry_run", "cases": [],
                              "summary": _summary([])}
    try:
        prompt, limits, metadata = load_manifest(args.manifest, devon_root)
        report["manifest"] = metadata
        cases = load_inputs(args.cases)
        if getattr(args, "selection_path", None) is not None:
            from case_selection import resolve_selection, filter_cases
            selection = resolve_selection(args.selection_path, lab_root=LAB_ROOT,
                cases_path=args.cases, experiment="B", split=args.split)
            if prompt.model not in selection.model_ids:
                raise LabError("selection_model_mismatch")
            cases = filter_cases(cases, selection)
        selected = [case for case in cases if args.split == "all" or
                    case.envelope["control"]["split"] == args.split]
        if not selected:
            raise LabError("no_cases_selected")
        for case in selected:
            report["cases"].append(await validate_case(case, args.cases, prompt, limits))
            report["summary"] = _summary(report["cases"])
            await output.checkpoint(report)
        output.save(report, "completed")
        return output.latest
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            code = "run_interrupted"
        elif isinstance(error, LabError):
            code = error.code
        elif isinstance(error, (ImportError, ModuleNotFoundError)):
            code = "dependency_unavailable"
        else:
            code = "offline_validation_failed"
        report["summary"]["status"] = "interrupted" if code == "run_interrupted" else "failed"
        output.latest = report
        output.stop("interrupted" if code == "run_interrupted" else "failed", code)
        if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
        return output.latest


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except FileExistsError:
        print(json.dumps({"status": "failed", "validation_scope": "validated_only", "model_calls": 0,
                          "error": {"code": "output_exists"}}), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(json.dumps({"status": "interrupted", "validation_scope": "validated_only", "model_calls": 0,
                          "error": {"code": "run_interrupted"}}), file=sys.stderr)
        return 130
    except Exception as error:
        code = error.code if isinstance(error, LabError) else "offline_validation_failed"
        print(json.dumps({"status": "failed", "validation_scope": "validated_only", "model_calls": 0,
                          "error": {"code": code}}), file=sys.stderr)
        return 1
    print(json.dumps(result["summary"], sort_keys=True))
    return int(result.get("run_state") != "completed" or
               result["summary"]["rejected_cases"] > 0 or not result["summary"]["total_cases"])


if __name__ == "__main__":
    raise SystemExit(main())
