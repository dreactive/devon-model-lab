"""Lab-only typed recovery injection around the original service/runtime.

This module creates no transports or credentials. Normal cases delegate to the
original ServiceExecutor. Recovery observations are separate from service_input
and never become raw source material, permitted references, or review approval.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import re
from typing import Any, Mapping

from devon_ai import contracts as c
from devon_ai.agents.director.agent import _references
from devon_ai.agents.director.runtime import (
    RecoveryFeedback, _feedback_payload, _validate_candidate, run_director,
)
from scripts.ai_eval_bridge import ServiceExecutor, _attempts, prepare
from eval_runner import Execution, ExecutionError
from judge_context import MAX_CONTEXT_BYTES, build_judge_context, validate_judge_context
from jsonschema import Draft202012Validator

JUDGE_CONTEXT_VERSION = "lab-recovery-judge-context.v1"
OBSERVATION_VERSION = "synthetic-rejected-candidate.v1"
_ROW_FIELDS = {"case_id", "version", "category", "scope", "runtime_input", "authoring_input", "verification_expected"}
_SIDECAR_FIELDS = {"case_id", "version", "scope", "recovery_feedback"}
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def _bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _task_limits(limits: c.CallLimits, overrides: Mapping[str, Any] | None) -> dict[str, c.CallLimits]:
    result = {}
    for task, value in (overrides or {}).items():
        if type(task) is not str:
            raise ValueError("recovery_task_limits_invalid")
        if type(value) is c.CallLimits:
            result[task] = value
        elif type(value) is dict:
            result[task] = replace(limits, **value)
        else:
            raise ValueError("recovery_task_limits_invalid")
    return result


def _document(path: Path, *, max_bytes: int = 1048576) -> Any:
    from score_eval import read_json
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("recovery_document_invalid")
    return read_json(path)


def _identity(case_id: object, version: object) -> None:
    if type(case_id) is not str or not _IDENTIFIER.fullmatch(case_id) or type(version) is not int or version < 1:
        raise ValueError("recovery_identity_invalid")


def _path(root: Path, relative: object, expected: str) -> Path:
    if type(relative) is not str or relative != expected:
        raise ValueError("recovery_path_invalid")
    target = (root / relative).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("recovery_path_invalid")
    return target


def catalogue_rows(root: Path) -> list[dict[str, Any]]:
    """Validate catalogue identity/path metadata without reading labels."""
    root = Path(root).resolve(strict=True)
    raw = _document(root / "catalogue.json")
    if type(raw) is not dict or set(raw) != {"version", "cases"} or type(raw["version"]) is not int or raw["version"] != 1 or type(raw["cases"]) is not list:
        raise ValueError("recovery_catalogue_invalid")
    seen = set()
    for row in raw["cases"]:
        if type(row) is not dict or set(row) != _ROW_FIELDS:
            raise ValueError("recovery_catalogue_invalid")
        _identity(row["case_id"], row["version"])
        identity = row["case_id"], row["version"]
        if identity in seen or row["category"] not in {f"A{i}" for i in range(1, 11)} or row["scope"] not in {"service", "recovery_component"}:
            raise ValueError("recovery_catalogue_invalid")
        seen.add(identity)
        stem = f"{row['case_id']}.v{row['version']}.json"
        if row["authoring_input"] != f"authoring/{stem}" or row["verification_expected"] not in {None, "retrieve", "skip"}:
            raise ValueError("recovery_catalogue_invalid")
        if row["scope"] == "recovery_component":
            if row["category"] != "A10" or row["runtime_input"] != f"runtime_inputs/{stem}" or row["verification_expected"] is not None:
                raise ValueError("recovery_catalogue_invalid")
        elif row["runtime_input"] is not None or row["category"] == "A10":
            raise ValueError("recovery_catalogue_invalid")
    return raw["cases"]


def _feedback(sidecar: object, *, identity: tuple[str, int] | None = None) -> RecoveryFeedback:
    if type(sidecar) is not dict or set(sidecar) != _SIDECAR_FIELDS or sidecar.get("scope") != "recovery_component":
        raise ValueError("recovery_sidecar_invalid")
    _identity(sidecar["case_id"], sidecar["version"])
    if identity is not None and (sidecar["case_id"], sidecar["version"]) != identity:
        raise ValueError("recovery_identity_mismatch")
    raw = sidecar["recovery_feedback"]
    if type(raw) is not dict or set(raw) != {"previous_candidate", "recovery"}:
        raise ValueError("recovery_sidecar_invalid")
    return RecoveryFeedback(c.decode_strict(c.Question, raw["previous_candidate"]),
                            c.decode_strict(c.CandidateRecovery, raw["recovery"]))


@dataclass(frozen=True)
class RecoveryCase:
    case_id: str
    version: int
    payload: dict[str, Any]
    feedback: RecoveryFeedback
    sidecar: dict[str, Any]
    sidecar_path: str
    sidecar_sha256: str
    source_context: dict[str, Any]


def inspect_recovery(root: Path, case_id: str, version: int = 1) -> RecoveryCase | None:
    """Resolve a component only from its actual input, typed sidecar and catalogue."""
    _identity(case_id, version)
    root = Path(root).resolve(strict=True)
    rows = catalogue_rows(root)
    row = next((item for item in rows if (item["case_id"], item["version"]) == (case_id, version)), None)
    if row is None:
        raise ValueError("recovery_case_not_catalogued")
    if row["scope"] != "recovery_component":
        return None
    relative = f"inputs/{case_id}.v{version}.json"
    envelope = _document(_path(root, relative, relative))
    if type(envelope) is not dict or set(envelope) != {"case_id", "version", "control", "payload"} or (envelope["case_id"], envelope["version"]) != (case_id, version):
        raise ValueError("recovery_input_identity_mismatch")
    control = envelope["control"]
    if type(control) is not dict or set(control) != {"kind", "split", "source_group_id", "synthetic"} or control["kind"] != "question" or control["split"] not in {"dev", "holdout"} or control["synthetic"] is not True or type(control["source_group_id"]) is not str or not control["source_group_id"].strip():
        raise ValueError("recovery_input_control_invalid")
    task, data = prepare("question", envelope["payload"])
    if task != "director":
        raise ValueError("recovery_task_invalid")
    expected = f"runtime_inputs/{case_id}.v{version}.json"
    sidecar_path = _path(root, row["runtime_input"], expected)
    sidecar = _document(sidecar_path, max_bytes=32768)
    feedback = _feedback(sidecar, identity=(case_id, version))
    # The observed rejection may be semantically wrong, but references, contract
    # structure, parent and persona must still satisfy the original validator.
    _validate_candidate(feedback.previous_candidate, data["context"],
                        _references(data["context"], data["reference_texts"]))
    digest = hashlib.sha256(sidecar_path.read_bytes()).hexdigest()
    return RecoveryCase(case_id, version, envelope["payload"], feedback, sidecar,
                        expected, digest, validate_judge_context(build_judge_context(envelope["payload"])))


def _provenance(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"path", "sha256"} or type(value["path"]) is not str or not re.fullmatch(r"runtime_inputs/[A-Za-z0-9][A-Za-z0-9_-]{0,127}\.v[1-9][0-9]*\.json", value["path"]) or type(value["sha256"]) is not str or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"]):
        raise ValueError("recovery_provenance_invalid")
    return dict(value)


def build_recovery_judge_context(payload: dict[str, Any], sidecar: dict[str, Any], *,
                                 provenance: dict[str, str] | None = None) -> dict[str, Any]:
    """Strict versioned observation envelope; base context stays source-owned."""
    feedback = _feedback(sidecar)
    task, data = prepare("question", payload)
    if task != "director":
        raise ValueError("recovery_task_invalid")
    _validate_candidate(feedback.previous_candidate, data["context"], _references(data["context"], data["reference_texts"]))
    result = {"schema_version": JUDGE_CONTEXT_VERSION,
              "source_context": validate_judge_context(build_judge_context(payload)),
              "recovery_observation": {"schema_version": OBSERVATION_VERSION,
                  "previous_candidate": json.loads(_bytes(asdict(feedback.previous_candidate))),
                  "recovery": json.loads(_bytes(asdict(feedback.recovery))), "provenance": _provenance(provenance)}}
    # Validate the real downstream projection now, including its combined budget.
    recovery_judge_context_adapter(result)
    return result


def recovery_judge_context_adapter(value: object) -> dict[str, Any]:
    """Return original ModelJudge context with a surviving non-source observation.

    Every projected key is owned by the original projector. Its explicit
    prior_candidate_is_not_raw_source limitation is retained. No Judge prompt,
    output schema or grader is replaced, and no paid Judge entry is exposed.
    """
    if type(value) is not dict or set(value) != {"schema_version", "source_context", "recovery_observation"} or value["schema_version"] != JUDGE_CONTEXT_VERSION:
        raise ValueError("recovery_judge_context_invalid")
    base = validate_judge_context(value["source_context"])
    observation = value["recovery_observation"]
    if type(observation) is not dict or set(observation) != {"schema_version", "previous_candidate", "recovery", "provenance"} or observation["schema_version"] != OBSERVATION_VERSION:
        raise ValueError("recovery_judge_context_invalid")
    feedback = RecoveryFeedback(c.decode_strict(c.Question, observation["previous_candidate"]),
                                c.decode_strict(c.CandidateRecovery, observation["recovery"]))
    _feedback_payload(feedback)
    provenance = _provenance(observation["provenance"])
    result = copy.deepcopy(base)
    target = result["source"].get("service_input")
    if type(target) is not dict or "rejected_candidate" in target:
        raise ValueError("recovery_judge_observation_collision")
    projected = {"version": OBSERVATION_VERSION, "question": asdict(feedback.previous_candidate),
                 "reason": {"kind": feedback.recovery.recovery, "summary": feedback.recovery.reason_summary},
                 "source_kind": "synthetic_observation"}
    if provenance is not None:
        projected["source_location"] = {"path": provenance["path"], "text_hash": provenance["sha256"]}
    target["rejected_candidate"] = projected
    result["limitations"] = sorted(set(result["limitations"]) | {"prior_candidate_is_not_raw_source"})
    if len(_bytes(result)) > MAX_CONTEXT_BYTES:
        raise ValueError("recovery_judge_context_too_large")
    checked = validate_judge_context(result)
    if checked["source"].get("service_input", {}).get("rejected_candidate") != json.loads(_bytes(projected)):
        raise ValueError("recovery_judge_observation_discarded")
    return checked


async def capture_director_request(payload: dict[str, Any], prompts: Mapping[str, c.PromptSpec],
                                   limits: c.CallLimits, *,
                                   task_limits: Mapping[str, c.CallLimits] | None = None,
                                   feedback: RecoveryFeedback | None = None) -> dict[str, Any]:
    """Capture the actual original plan request, validate schema/bytes, stop locally."""
    from app.integrations.llm.client import request_size
    task, data = prepare("question", payload)
    if task != "director" or "director" not in prompts:
        raise ExecutionError("input", "capture_director_required")
    normalized = _task_limits(limits, task_limits)
    captured = []

    async def capture(request, validator):
        request = replace(request, limits=normalized.get(request.prompt.task_name, request.limits))
        expected = _feedback_payload(feedback) if feedback is not None else None
        if request.payload.get("operation") != "plan" or request.payload.get("recovery_feedback") != expected:
            raise ExecutionError("input", "captured_director_feedback_mismatch")
        Draft202012Validator.check_schema(request.output_schema)
        size = request_size(request)
        if size > request.limits.max_input_bytes:
            raise ExecutionError("input", "captured_director_request_too_large")
        captured.append({"request_bytes": size, "schema_version": request.schema_version,
                         "schema_sha256": hashlib.sha256(_bytes(request.output_schema)).hexdigest(),
                         "recovery_feedback_present": expected is not None, "model_calls": 0})
        return c.ModelResult(None, c.CallFailure("budget", "lab_dry_capture", "No model call executed."), ())

    result = await run_director(data["context"], prompt=prompts["director"], limits=limits,
        model_call=capture, answer_analysis=data.get("answer_analysis"),
        reference_texts=data["reference_texts"], tool_results=data["tool_results"], recovery_feedback=feedback)
    if len(captured) != 1 or result.failure is None or result.failure.error_code != "lab_dry_capture" or result.attempts:
        raise ExecutionError("input", "captured_director_runtime_rejected")
    return captured[0]


async def capture_recovery_judge_request(component: RecoveryCase, prompt: c.PromptSpec,
                                          limits: c.CallLimits) -> dict[str, Any]:
    """Prove the actual original ModelJudge request retains a typed observation.

    Uses only a local sentinel ModelCall. The local connection-check rubric is
    unrelated to benchmark criteria and cannot create a model verdict or trace.
    """
    from app.integrations.llm.client import request_size
    from scripts.ai_model_judge import ModelJudge
    if type(component) is not RecoveryCase or prompt.task_name != "evaluation_judge" or prompt.version.partition("@")[0] != "evaluation_judge_v3":
        raise ValueError("recovery_judge_capture_configuration_invalid")
    envelope = build_recovery_judge_context(component.payload, component.sidecar,
        provenance={"path": component.sidecar_path, "sha256": component.sidecar_sha256})
    context = recovery_judge_context_adapter(envelope)
    expected = context["source"]["service_input"]["rejected_candidate"]
    captured = []

    async def capture(request, validator):
        observed = request.payload.get("source_context", {}).get("source", {}).get("service_input", {}).get("rejected_candidate")
        if observed != expected or request.prompt != prompt:
            raise ValueError("recovery_judge_capture_projection_invalid")
        Draft202012Validator.check_schema(request.output_schema)
        size = request_size(request)
        if size > request.limits.max_input_bytes:
            raise ValueError("recovery_judge_capture_request_too_large")
        captured.append({"request_bytes": size, "schema_version": request.schema_version,
            "schema_sha256": hashlib.sha256(_bytes(request.output_schema)).hexdigest(),
            "prompt_version": prompt.version, "prompt_sha256": hashlib.sha256(prompt.template.encode("utf-8")).hexdigest(),
            "recovery_observation_present": True, "model_calls": 0})
        return c.ModelResult(None, c.CallFailure("budget", "lab_dry_capture", "No Judge call executed."), ())

    judge = ModelJudge(prompt, limits, lambda: capture)
    judgment = await judge.judge_with_context(
        {"allowed": [{"id": "connection-check", "description": "Inspect context connection only."}], "forbidden": []},
        "{}", context)
    if len(captured) != 1 or judgment.verdict is not None or judgment.attempts or judgment.failure is None or judgment.failure.get("error_code") != "lab_dry_capture":
        raise ValueError("recovery_judge_original_capture_failed")
    return captured[0]


class RecoveryExecutor:
    def __init__(self, root: Path, prompts: Mapping[str, c.PromptSpec], limits: c.CallLimits,
                 model_call_factory, *, dry_run: bool = False,
                 task_limits: Mapping[str, c.CallLimits] | None = None):
        self.root, self.prompts, self.limits = Path(root).resolve(strict=True), prompts, limits
        self.model_call_factory, self.dry_run = model_call_factory, dry_run
        self.task_limits = _task_limits(limits, task_limits)
        self.original = ServiceExecutor(prompts, limits, model_call_factory,
                                        dry_run=dry_run, task_limits=self.task_limits)

    def _resolve(self, payload: dict[str, Any]) -> RecoveryCase | None:
        if not (self.root / "catalogue.json").is_file():
            return None
        interview_id = payload.get("service_input", {}).get("context", {}).get("interview_id")
        matched = []
        for row in catalogue_rows(self.root):
            relative = f"inputs/{row['case_id']}.v{row['version']}.json"
            stored = _document(_path(self.root, relative, relative))
            if stored.get("payload", {}).get("service_input", {}).get("context", {}).get("interview_id") == interview_id:
                matched.append((row, stored))
        if len(matched) > 1:
            raise ExecutionError("input", "recovery_interview_identity_duplicate")
        if not matched or matched[0][0]["scope"] != "recovery_component":
            return None
        row, stored = matched[0]
        if _bytes(payload) != _bytes(stored["payload"]):
            raise ExecutionError("input", "recovery_payload_identity_mismatch")
        return inspect_recovery(self.root, row["case_id"], row["version"])

    async def __call__(self, kind: str, payload: dict[str, Any]) -> Execution:
        task, data = prepare(kind, payload)
        case = self._resolve(payload) if kind in {"question", "flow"} else None
        if case is None:
            return await self.original(kind, payload)
        if task != "director" or "director" not in self.prompts:
            raise ExecutionError("configuration", "recovery_director_prompt_missing")
        if self.prompts["director"].version.partition("@")[0] not in {"director_v7", "director_v8"}:
            raise ExecutionError("configuration", "recovery_prompt_unsupported")
        attempts: list[c.AttemptMetadata] = []
        captured: list[int] = []

        async def capture(request, validator):
            from app.integrations.llm.client import request_size
            if request.payload.get("operation") != "plan" or request.payload.get("recovery_feedback") != _feedback_payload(case.feedback):
                raise ExecutionError("input", "recovery_feedback_not_in_original_request")
            Draft202012Validator.check_schema(request.output_schema)
            size = request_size(request)
            if size > request.limits.max_input_bytes:
                raise ExecutionError("input", "recovery_request_too_large")
            captured.append(size)
            return c.ModelResult(None, c.CallFailure("budget", "lab_dry_capture", "No model call executed."), ())

        call = capture if self.dry_run else self.model_call_factory()

        async def tracked(request, validator):
            request = replace(request, limits=self.task_limits.get(request.prompt.task_name, request.limits))
            result = await call(request, validator)
            attempts.extend(result.attempts)
            return result

        try:
            result = await run_director(data["context"], prompt=self.prompts["director"], limits=self.limits,
                model_call=tracked, answer_analysis=data.get("answer_analysis"),
                reference_texts=data["reference_texts"], tool_results=data["tool_results"],
                recovery_feedback=case.feedback)
            if self.dry_run:
                if len(captured) != 1 or result.failure is None or result.failure.error_code != "lab_dry_capture" or result.attempts:
                    raise ExecutionError("input", "recovery_original_runtime_capture_failed")
                return Execution({"service_task": task, "input_valid": True, "execution_scope": "recovery_component",
                    "recovery_feedback_present": True, "request_bytes": captured[0], "model_calls": 0}, validated_only=True)
            if result.failure is not None or result.data is None:
                failure = result.failure
                raise ExecutionError(failure.stage if failure else "semantic", failure.error_code if failure else "no_output")
            return Execution({"decision": asdict(result.data.decision.data),
                "question": None if result.data.question is None else asdict(result.data.question.data)}, _attempts(attempts))
        except ExecutionError as error:
            raise ExecutionError(error.stage, error.code, _attempts(attempts)) from None
        except c.ContractError as error:
            raise ExecutionError(error.stage, "service_contract_rejected", _attempts(attempts)) from None
        except Exception as error:
            raise ExecutionError("executor", type(error).__name__, _attempts(attempts)) from None
