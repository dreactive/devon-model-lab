"""Export source-owned schemas and strict lab envelopes without writing to DEVON.

Run with Python -B. SCORE_CRITERIA is read with ast.literal_eval; its module is
never imported. Semantic validation remains owned by the original service.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from types import UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

sys.dont_write_bytecode = True
LAB_ROOT = Path(__file__).resolve().parents[1]
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))


def object_schema(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def array_schema(items: dict, **bounds: int) -> dict:
    return {"type": "array", "items": items, **bounds}


def contract_schema(annotation: object) -> dict:
    """Structural schema from original dataclass fields; never replaces validators."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Literal:
        return {"enum": list(args)}
    if origin in (Union, UnionType):
        return {"anyOf": [contract_schema(item) for item in args]}
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        return array_schema(contract_schema(args[0]))
    scalar = {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null"}
    if annotation in scalar:
        return {"type": scalar[annotation], **({"pattern": r"\S"} if annotation is str else {})}
    if is_dataclass(annotation):
        hints = get_type_hints(annotation)
        declared = fields(annotation)
        return object_schema(
            {item.name: contract_schema(hints[item.name]) for item in declared},
            [item.name for item in declared
             if item.default is MISSING and item.default_factory is MISSING],
        )
    raise TypeError("Unsupported original contract annotation")


def extract_rubrics(devon_root: Path) -> dict[str, dict[str, str]]:
    """Read literal keyword data without evaluating a call or executing seed code."""
    tree = ast.parse((devon_root / "backend/scripts/seed_score_criteria.py").read_text(encoding="utf-8"))
    assignment = next(node for node in tree.body if isinstance(node, ast.AnnAssign)
                      and isinstance(node.target, ast.Name) and node.target.id == "SCORE_CRITERIA")
    if not isinstance(assignment.value, ast.Tuple):
        raise ValueError("Rubric literal tuple required")
    result = {}
    for node in assignment.value.elts:
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "ScoreCriterionSpec" or node.args:
            raise ValueError("Unexpected rubric source structure")
        keywords = {item.arg: item.value for item in node.keywords}
        key = ast.literal_eval(keywords["score_key"])
        levels = ast.literal_eval(keywords["rubric"])
        if key in result or set(levels) != {str(level) for level in range(5)} or not all(type(text) is str and text for text in levels.values()):
            raise ValueError("Invalid rubric literal data")
        result[key] = levels
    if len(result) != 6:
        raise ValueError("Exactly six rubric keys required")
    return result


def lab_schemas(c: object) -> dict[str, dict]:
    text = {"type": "string", "minLength": 1}
    texts = array_schema(text)
    personas = {"enum": ["hr_manager", "tech_lead", "domain_lead"]}
    keys = list(get_args(c.ScoreKeyId))
    control = lambda kind: object_schema({"kind": {"const": kind}, "split": {"enum": ["dev", "holdout"]},
                                         "source_group_id": text, "synthetic": {"const": True}})
    envelope = lambda kind, task, service: object_schema({
        "case_id": text, "version": {"type": "integer", "minimum": 1},
        "control": control(kind), "payload": object_schema({
            "service_task": {"const": task}, "service_input": service})})
    reference = object_schema({"kind": contract_schema(c.BasisRef)["properties"]["kind"], "id": text,
                               "text": {"type": "string"}})
    location = array_schema(text, minItems=3, maxItems=3)
    question_service = object_schema({
        "context": contract_schema(c.Context), "question": contract_schema(c.Question),
        "answer_text": text, "turn_id": text,
        "allowed_locations": array_schema(location), "reference_texts": array_schema(reference),
        "tool_results": array_schema(contract_schema(c.ToolResult)),
        "answer_analysis": {"anyOf": [contract_schema(c.AnswerAnalysis), {"type": "null"}]},
    }, ["context"])
    question = envelope("question", "director", question_service)
    question["properties"]["payload"]["properties"]["service_task"] = {"enum": ["director", "director_verification"]}
    # BE evidence names are an explicit adapter over the original Evidence type.
    evidence_fields = contract_schema(c.Evidence)["properties"]
    evidence = object_schema({
        ("id" if name == "evidence_id" else "source_type" if name == "source_kind" else
         "snippet" if name == "content" else name): definition
        for name, definition in evidence_fields.items()
    }, ["id", "repository_id", "git_ref", "source_type", "path", "metadata_key", "snippet", "tool_name"])
    turn = object_schema({
        "turn_no": {"type": "integer", "minimum": 1, "maximum": 9}, "persona": personas,
        "question": text, "answer": {"type": ["string", "null"]},
        "question_contract": contract_schema(c.QuestionContract),
        "analysis": {"anyOf": [contract_schema(c.AnswerAnalysis), {"type": "null"}]},
        "parent_turn_no": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": 9}, {"type": "null"}]},
        "jd_requirement_ids": texts, "evidences": array_schema(evidence),
    })
    rubric = object_schema({key: object_schema({str(level): text for level in range(5)}) for key in keys})
    report = envelope("report", "report", object_schema({
        "turns": array_schema(turn, minItems=9, maxItems=9),
        "requirements": array_schema(contract_schema(c.LinkedRequirement)),
        "rubrics": rubric, "tool_results": array_schema(contract_schema(c.ReportToolResult)),
        "limitations": texts, "supplemental_sources": array_schema(contract_schema(c.SupplementalSource)),
        "source_notes": array_schema(contract_schema(c.JDSourceNote)),
    }, ["turns", "requirements", "rubrics", "tool_results", "limitations"]))
    review_fields = object_schema({
        "status": {"enum": ["unreviewed", "approved", "pending", "invalid"]},
        "author": {"const": "Codex"},
        "reviewer": {"anyOf": [text, {"type": "null"}]},
        "reviewed_at": {"anyOf": [text, {"type": "null"}]}, "pending_notes": texts,
    })
    # Authorship is fixed to this draft producer. Distinctness is consequently
    # expressible in standard JSON Schema; general author identity comparisons
    # still belong to the original semantic review validator.
    review_fields["allOf"] = [{
        "if": {"properties": {"status": {"const": "approved"}}},
        "then": {"properties": {
            "reviewer": {"type": "string", "pattern": r"\S", "not": {"pattern": r"^\s*[Cc][Oo][Dd][Ee][Xx]\s*$"}},
            "reviewed_at": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$"},
            "pending_notes": {"maxItems": 0}}},
        "else": {"properties": {"pending_notes": {"minItems": 1}}},
    }, {"if": {"properties": {"status": {"const": "unreviewed"}}},
        "then": {"properties": {"reviewer": {"type": "null"}, "reviewed_at": {"type": "null"}}}}]
    review = object_schema({"case_id": text, "version": {"type": "integer", "minimum": 1}, "review": review_fields})
    level = {"enum": [0, 1, 2, 3, 4, "not_applicable"]}
    gold_item = object_schema({
        "turn_id": {"type": "string", "pattern": "^[1-9]$"}, "key": {"enum": keys},
        "level": level, "acceptable": array_schema(level, minItems=1, uniqueItems=True),
        "rationale": {"type": "string", "pattern": "\\S"},
        "rubric_quote": {"type": "string", "pattern": "\\S"},
    }, ["turn_id", "key", "level", "rationale"])
    gold_item["allOf"] = [{
        "if": {"properties": {"level": {"const": "not_applicable"}}},
        "then": {"not": {"required": ["rubric_quote"]}},
        "else": {"required": ["rubric_quote"]},
    }]
    return {"question-input.schema.json": question, "report-input.schema.json": report,
            "gold.schema.json": array_schema(gold_item, minItems=1), "review.schema.json": review}


def fingerprint(path: Path, root: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def director_output_schemas(payload: dict, prompt: object) -> dict[str, dict]:
    """Call source-owned dynamic schema builders with this exact prepared input."""
    from devon_ai.agents.director.agent import _references
    from devon_ai.agents.director.runtime import SUPPORTED_PROMPT_VERSIONS, _bounded_plan_schema, _plan_schema, _review_schema
    from scripts.ai_eval_bridge import prepare
    task, data = prepare("question", payload)
    version = prompt.version.partition("@")[0]
    if task != "director" or prompt.task_name != "director" or version not in SUPPORTED_PROMPT_VERSIONS:
        raise ValueError("director_schema_input_invalid")
    context = data["context"]
    coverage = bool(context.evaluation_targets) and version not in {"director_v1", "director_v2"}
    plan = (_bounded_plan_schema(context, _references(context, data["reference_texts"]), coverage)
            if version in {"director_v6", "director_v7", "director_v8"} else _plan_schema(coverage))
    return {"director-plan": plan, "director-review": _review_schema()}


def export_question_case_schemas(cases_root: Path, output: Path, prompt: object) -> list[dict]:
    """Export case-bound source schemas; never read expectations or rewrite cases."""
    from jsonschema import Draft202012Validator
    from score_eval import read_json
    root, output = Path(cases_root).resolve(strict=True), Path(output).resolve()
    if output != LAB_ROOT and LAB_ROOT not in output.parents:
        raise ValueError("schema_output_outside_lab")
    records = []
    pending = []
    identities = set()
    for path in sorted((root / "inputs").glob("*.json")):
        envelope = read_json(path)
        case_id, version = envelope.get("case_id"), envelope.get("version")
        if (type(case_id) is not str or not case_id or type(version) is not int or version < 1
                or path.name != f"{case_id}.v{version}.json" or (case_id, version) in identities):
            raise ValueError("schema_case_identity_invalid")
        identities.add((case_id, version))
        schemas = director_output_schemas(envelope["payload"], prompt)
        name = f"director-plan.{case_id}.v{version}.schema.json"
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        encoded = json.dumps(schemas["director-plan"], ensure_ascii=False, indent=2) + "\n"
        pending.append((name, encoded))
        records.append({"case_id": case_id, "version": version,
            "input_path": path.relative_to(root).as_posix(), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "schema_path": name, "schema_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "prompt_version": prompt.version, "generator": "original runtime dynamic schema builder; exact prepared input"})
    if not records:
        raise ValueError("schema_cases_missing")
    output.mkdir(parents=True, exist_ok=True)
    for name, encoded in pending:
        (output / name).write_text(encoded, encoding="utf-8", newline="\n")
    (output / "provenance.json").write_text(json.dumps({"schema_version": "lab-case-schemas.v1", "cases": records},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devon-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=LAB_ROOT / "schemas")
    parser.add_argument("--director-prompt", default="ai/prompts/director-runtime-v8.md")
    parser.add_argument("--answer-analysis-prompt", default="ai/prompts/answer-analysis-runtime-v6.md")
    parser.add_argument("--report-score-prompt", default="ai/prompts/report-score-v3.md")
    parser.add_argument("--question-cases", type=Path, help="Optional actual corpus root for additional case-bound Director schemas.")
    args = parser.parse_args()
    source, output = args.devon_root.resolve(strict=True), args.output.resolve()
    if output == source or source in output.parents:
        parser.error("Schema output must be outside DEVON")
    if output != LAB_ROOT and LAB_ROOT not in output.parents:
        parser.error("Schema output must be inside model-lab")
    sys.path.insert(0, str(source / "ai/src"))
    from devon_ai import contracts as c
    from devon_ai.agents.director.agent import _references
    from devon_ai.agents.director.runtime import _bounded_plan_schema, _review_schema
    from devon_ai.llm_tasks import answer_analysis_wire as wire
    from devon_ai.llm_tasks.report_score import _output_schema

    question_path = LAB_ROOT / "cases/question/inputs/q-lab-smoke-0001.v1.json"
    report_path = LAB_ROOT / "cases/answer/inputs/b-lab-smoke-0001.v1.json"
    question = json.loads(question_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    context = c.decode_strict(c.Context, question["payload"]["service_input"]["context"])
    turn = report["payload"]["service_input"]["turns"][0]
    analysis_keys = tuple(point["key"] for point in turn["question_contract"]["required_points"])
    units = wire.answer_units(turn["answer"])
    schemas = lab_schemas(c)
    schemas.update({
        "director-plan.q-lab-smoke-0001.v1.schema.json": _bounded_plan_schema(context, _references(context, {}), True),
        "director-review.schema.json": _review_schema(),
        "report-score.schema.json": _output_schema(),
        "answer-analysis-v6.b-lab-smoke-0001.turn-1.schema.json": wire.output_schema(analysis_keys, units, frozenset(), frozenset()),
    })
    rubrics = extract_rubrics(source)
    if rubrics != report["payload"]["service_input"]["rubrics"]:
        raise ValueError("Fixture rubric differs from original literal data")
    paths = ["backend/scripts/seed_score_criteria.py", "ai/src/devon_ai/contracts.py",
             "ai/src/devon_ai/agents/director/agent.py", "ai/src/devon_ai/agents/director/runtime.py",
             "ai/src/devon_ai/llm_tasks/answer_analysis_wire.py", "ai/src/devon_ai/llm_tasks/answer_analysis.py",
             "ai/src/devon_ai/llm_tasks/report_score.py", "ai/src/devon_ai/llm_tasks/report.py",
             args.director_prompt, args.answer_analysis_prompt, args.report_score_prompt]
    provenance = {
        "scope": "Unreviewed synthetic structural exports; no model execution or semantic calibration.",
        "rubric_extraction": "SCORE_CRITERIA AST literal keyword values; seed module never executed.",
        "rubric_rows": sum(map(len, rubrics.values())),
        "sources": [fingerprint(source / path, source) for path in paths],
        "fixture_sources": [fingerprint(path, LAB_ROOT) for path in (question_path, report_path)],
        "generators": {
            "director-plan.q-lab-smoke-0001.v1.schema.json": "runtime._bounded_plan_schema(context, _references(context, {}), True); director_v8",
            "director-review.schema.json": "runtime._review_schema()",
            "report-score.schema.json": "report_score._output_schema()",
            "answer-analysis-v6.b-lab-smoke-0001.turn-1.schema.json": "answer_analysis_wire.output_schema(required point keys, answer_units(turn 1), empty evidence, empty locations)",
        },
        "lab_envelopes": "Strict lab-only structural bounds; original service semantic validation remains mandatory.",
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas.items():
        (output / name).write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.question_cases is not None:
        prompt = c.PromptSpec("director", "director_v8", "schema-export-only",
                              (source / args.director_prompt).read_text(encoding="utf-8"))
        # Original prepare uses scripts.ai_eval_bridge from the read-only backend.
        for path in (source / "backend", source / "ai/evals"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        export_question_case_schemas(args.question_cases, output / "generated/question", prompt)
    print(f"Exported {len(schemas)} schemas; rubric rows: {provenance['rubric_rows']}; no provider calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
