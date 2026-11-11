"""Offline, content-bound execution approval. This module never reads .env or sends HTTP.

Plans contain hashes of evaluation annotations as well as service inputs. Those
annotations stay out of model requests; their hashes make changed criteria require
fresh approval. Approval is consumed only after complete preflight verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from cost_accounting import estimate_cost, load_pricing

LAB_ROOT = Path(__file__).resolve().parent
SOURCE_REQUIRED = (
    "backend/app/integrations/llm/client.py",
    "backend/app/core/config.py",
    "backend/app/llm_tasks/report.py",
    "backend/app/db/models/interview.py",
    "backend/app/db/models/report.py",
    "backend/scripts/run_ai_evaluation.py",
    "backend/scripts/ai_eval_bridge.py",
    "backend/scripts/ai_model_judge.py",
    "backend/scripts/evaluation_output.py",
    "ai/src/devon_ai/contracts.py",
    "ai/src/devon_ai/agents/director/runtime.py",
    "ai/src/devon_ai/llm_tasks/report_score.py",
    "ai/src/devon_ai/llm_tasks/report.py",
    "ai/evals/eval_cases.py",
    "ai/evals/eval_runner.py",
)
_LIMIT_KEYS = frozenset({"timeout_seconds", "max_output_tokens", "max_input_bytes",
                         "max_response_bytes", "reasoning_effort", "stream"})
_REQUIRED_LIMIT_KEYS = frozenset({"timeout_seconds", "max_output_tokens",
                                 "max_input_bytes", "max_response_bytes"})


class PolicyError(ValueError):
    """Only fixed, non-sensitive failure codes leave the policy boundary."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("json_invalid")
        result[key] = value
    return result


def _constant(_: str) -> Any:
    raise PolicyError("json_invalid")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise PolicyError("json_invalid")
    return parsed


def read_json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_object, parse_constant=_constant,
                          parse_float=_finite_float)
    except (OSError, UnicodeError, ValueError, RecursionError, TypeError):
        raise PolicyError("json_invalid") from None


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise PolicyError("plan_invalid") from None


def plan_digest(plan: dict) -> str:
    if type(plan) is not dict:
        raise PolicyError("plan_invalid")
    return hashlib.sha256(_canonical(plan)).hexdigest()


def _path(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise PolicyError("path_invalid")
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        raise PolicyError("path_invalid") from None


def _text(value: Any, code: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise PolicyError(code)
    return value


def _positive_int(value: Any, code: str) -> int:
    if type(value) is not int or value < 1:
        raise PolicyError(code)
    return value


def _budget(value: Any) -> Decimal | None:
    if value is None:
        return None
    if type(value) not in (Decimal, str, int):
        raise PolicyError("budget_invalid")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        raise PolicyError("budget_invalid") from None
    if not amount.is_finite() or amount <= 0:
        raise PolicyError("budget_invalid")
    return amount


def endpoint_hash(base_url: str) -> str:
    """Bind the exact explicit HTTPS route without writing its contents to a plan."""
    value = _text(base_url, "endpoint_invalid")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise PolicyError("endpoint_invalid")
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or not url.hostname or not url.netloc
                or url.username is not None or url.password is not None
                or url.query or url.fragment or "?" in value or "#" in value):
            raise ValueError
        # Accessing port catches malformed and out-of-range port strings.
        _ = url.port
    except (ValueError, TypeError):
        raise PolicyError("endpoint_invalid") from None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    resolved = _path(path)
    if root is not None and not resolved.is_relative_to(root):
        raise PolicyError("path_escape_rejected")
    try:
        raw = resolved.read_bytes()
    except OSError:
        raise PolicyError("fingerprint_missing") from None
    label = resolved.relative_to(root).as_posix() if root is not None else str(resolved)
    return {"path": label, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _dataset(root: Path, split: str, experiment: str,
             selected_keys: frozenset[tuple[str, int]] | None = None) -> tuple[list[dict], list[str]]:
    if not root.is_dir() or not (root / "inputs").is_dir():
        raise PolicyError("cases_invalid")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise PolicyError("cases_invalid")
    fingerprints, selected, seen, matched = [], [], set(), set()
    for path in files:
        fingerprints.append(_file(path, root=root))
        if path.suffix.lower() != ".json":
            continue
        raw = read_json(path)
        if path.parent != root / "inputs":
            continue
        if type(raw) is not dict or type(raw.get("control")) is not dict:
            raise PolicyError("cases_invalid")
        case_id = _text(raw.get("case_id"), "cases_invalid")
        if case_id in seen:
            raise PolicyError("cases_invalid")
        seen.add(case_id)
        control = raw["control"]
        if control.get("split") not in ("dev", "holdout"):
            raise PolicyError("cases_invalid")
        if split != "all" and control["split"] != split:
            continue
        expected_kind = "question" if experiment == "A" else "report"
        if control.get("kind") != expected_kind:
            raise PolicyError("case_experiment_mismatch")
        if selected_keys is not None:
            version = raw.get("version")
            if type(version) is not int or version < 1:
                raise PolicyError("case_identity_invalid")
            identity = case_id, version
            if identity not in selected_keys:
                continue
            matched.add(identity)
        selected.append(case_id)
    if selected_keys is not None and matched != selected_keys:
        raise PolicyError("selection_cases_mismatch")
    if not selected:
        raise PolicyError("no_cases_selected")
    return fingerprints, sorted(selected)


def _limits(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or not _REQUIRED_LIMIT_KEYS <= set(raw) <= _LIMIT_KEYS:
        raise PolicyError("manifest_invalid")
    timeout = raw["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise PolicyError("manifest_invalid")
    for name in _REQUIRED_LIMIT_KEYS - {"timeout_seconds"}:
        _positive_int(raw[name], "manifest_invalid")
    if raw.get("reasoning_effort") not in (None, "none", "minimal", "low", "medium", "high", "xhigh"):
        raise PolicyError("manifest_invalid")
    if type(raw.get("stream", False)) is not bool:
        raise PolicyError("manifest_invalid")
    # This runner and its usage accounting deliberately require nonstream responses.
    if raw.get("stream", False):
        raise PolicyError("streaming_execution_unsupported")
    return raw | {"reasoning_effort": raw.get("reasoning_effort"), "stream": False}


def _manifest(path: Path, devon: Path, experiment: str) -> tuple[list[dict], str, dict]:
    raw = read_json(path)
    if (type(raw) is not dict or not {"prompts", "limits"} <= set(raw)
            <= {"prompts", "limits", "task_limits"} or type(raw["prompts"]) is not list):
        raise PolicyError("manifest_invalid")
    limits = _limits(raw["limits"])
    overrides = raw.get("task_limits", {})
    if type(overrides) is not dict:
        raise PolicyError("manifest_invalid")
    for task, value in overrides.items():
        _text(task, "manifest_invalid")
        if type(value) is not dict or set(value) - _LIMIT_KEYS:
            raise PolicyError("manifest_invalid")
        _limits(limits | value)
    task_name = "director" if experiment == "A" else "report_score"
    prompts, entries = [], {}
    for item in raw["prompts"]:
        if type(item) is not dict or set(item) != {"task_name", "version", "model", "template_path"}:
            raise PolicyError("manifest_invalid")
        for value in item.values():
            _text(value, "manifest_invalid")
        if item["task_name"] in entries:
            raise PolicyError("manifest_invalid")
        resolved = (path.parent / item["template_path"]).resolve()
        if not resolved.read_text(encoding="utf-8-sig").strip():
            raise PolicyError("manifest_invalid")
        entries[item["task_name"]] = (item, resolved)
        prompts.append({"task": item["task_name"], "version": item["version"],
                        "model": item["model"], "file": _file(resolved)})
    if task_name not in entries:
        raise PolicyError("manifest_invalid")
    prompt, resolved = entries[task_name]
    runtime = read_json(devon / "ai/prompts/runtime-prompts.json")
    if type(runtime) is not dict or type(runtime.get(task_name)) is not dict:
        raise PolicyError("runtime_prompt_invalid")
    current = runtime[task_name]
    template = _text(current.get("template"), "runtime_prompt_invalid")
    runtime_path = (devon / "ai/prompts" / template).resolve()
    if not runtime_path.is_relative_to(devon / "ai/prompts"):
        raise PolicyError("runtime_prompt_invalid")
    if (prompt["version"] != current.get("version") or
            resolved.read_text(encoding="utf-8-sig") != runtime_path.read_text(encoding="utf-8-sig")):
        raise PolicyError("service_prompt_mismatch")
    return sorted(prompts, key=lambda row: row["task"]), prompt["model"], _limits(limits | overrides.get(task_name, {}))


def _sources(devon: Path) -> list[dict]:
    if not devon.is_dir() or any(not (devon / name).is_file() for name in SOURCE_REQUIRED):
        raise PolicyError("devon_source_invalid")
    files = {devon / name for name in SOURCE_REQUIRED}
    # Include transitive domain/runtime dependencies and their additions/removals.
    for relative in ("ai/src/devon_ai", "ai/evals", "backend/app/integrations/llm"):
        files.update((devon / relative).rglob("*.py"))
    files.add(devon / "ai/prompts/runtime-prompts.json")
    return [_file(path, root=devon) for path in sorted(files)]


def _lab_sources(lab: Path) -> list[dict]:
    """Recovery routing and generated contracts are part of the approved program."""
    files = set(lab.glob("*.py"))
    for relative, pattern in (("adapters", "*.py"), ("tools", "*.py"), ("schemas", "*.json")):
        files.update((lab / relative).rglob(pattern))
    return [_file(path, root=lab) for path in sorted(files)]


def build_plan(*, devon_root: str | Path, cases_path: str | Path,
               manifest_path: str | Path, pricing_path: str | Path,
               experiment: str, base_url: str, split: str = "dev", repeats: int = 1,
               budget_usd: Decimal | str | int | None = None,
               max_http_attempts: int | None = None,
               model_ids: list[str] | frozenset[str] | None = None,
               lab_root: str | Path | None = None,
               selection_path: str | Path | None = None,
               campaign_path: str | Path | None = None) -> dict:
    """Prepare a deterministic plan; absent user prices/caps create a blocked plan."""
    try:
        devon, lab = _path(devon_root), _path(lab_root or LAB_ROOT)
        cases, manifest, price_path = _path(cases_path), _path(manifest_path), _path(pricing_path)
        if lab.is_relative_to(devon):
            raise PolicyError("lab_inside_devon_rejected")
        if experiment not in ("A", "B") or split not in ("all", "dev", "holdout"):
            raise PolicyError("experiment_invalid")
        _positive_int(repeats, "repeats_invalid")
        amount = _budget(budget_usd)
        if max_http_attempts is not None:
            _positive_int(max_http_attempts, "http_attempt_cap_invalid")
        route = endpoint_hash(base_url)
        if campaign_path is not None:
            campaign_path = _path(campaign_path)
            if (not campaign_path.is_relative_to(lab / "campaigns") or not campaign_path.is_file()):
                raise PolicyError("campaign_path_rejected")
        selection = None
        if selection_path is not None:
            from case_selection import resolve_selection
            selection_path = _path(selection_path)
            selection = resolve_selection(selection_path, lab_root=lab, cases_path=cases,
                                          experiment=experiment, split=split)
        dataset, selected = _dataset(cases, split, experiment,
                                    None if selection is None else selection.case_keys)
        prompts, model, limits = _manifest(manifest, devon, experiment)
        if selection is not None and model not in selection.model_ids:
            raise PolicyError("selection_model_mismatch")
        if model_ids is not None and (type(model_ids) not in (list, frozenset, set, tuple)
                or any(type(item) is not str for item in model_ids) or set(model_ids) != {model}):
            raise PolicyError("executable_models_mismatch")
        pricing = load_pricing(price_path)
        prices = pricing["models"].get(model)
        blocked = []
        if amount is None:
            blocked.append("budget_missing")
        if max_http_attempts is None:
            blocked.append("http_attempt_cap_missing")
        if prices is None or prices["status"] != "collected":
            blocked.append("model_price_incomplete")
        estimate = None if max_http_attempts is None else estimate_cost(model,
            input_tokens_lower=0, input_tokens_upper=limits["max_input_bytes"],
            output_tokens_upper=limits["max_output_tokens"], calls_lower=0,
            calls_upper=max_http_attempts, pricing=pricing)
        upper = estimate["expected_upper_usd"] if estimate else None
        plan = {
            "version": 1, "purpose": "model-lab-guarded-execution",
            "config": {"devon_root": str(devon), "lab_root": str(lab),
                       "cases_path": str(cases), "manifest_path": str(manifest),
                       "pricing_path": str(price_path)},
            "experiment": experiment, "split": split, "repeats": repeats,
            "selected_case_ids": selected, "model_ids": [model], "limits": limits,
            "base_url_sha256": route,
            "budget_usd": format(amount, "f") if amount is not None else None,
            "max_http_attempts": max_http_attempts,
            "expected_lower_usd": "0" if upper is not None else None,
            "expected_upper_usd": upper,
            "estimated_upper_exceeds_budget": (Decimal(upper) > amount
                if upper is not None and amount is not None else None),
            "estimate_assumptions": [
                "Expected range is a planning allowance, not measured usage or a provider billing guarantee.",
                "Input upper uses max_input_bytes as token allowance on every HTTP attempt; output uses max_output_tokens.",
                "Upper uses the maximum user-provided base/cached input and base/reasoning output rates; lower is zero.",
                "Null optional rates add no guessed discount or surcharge to the estimate; observed nonzero special usage without its rate halts actual accounting as unconfirmed.",
                "The USD guard may stop before the HTTP attempt cap when the approved dollar balance is insufficient.",
            ],
            "fingerprints": {"cases": dataset, "manifest": _file(manifest),
                             "prompts": prompts, "pricing": _file(price_path),
                             "devon_source": _sources(devon), "lab_source": _lab_sources(lab)},
            "blocked_reasons": blocked,
        }
        if selection is not None:
            plan["config"]["selection_path"] = str(selection_path)
            plan["fingerprints"]["selection_document"] = _file(selection_path)
        if campaign_path is not None:
            plan["config"]["campaign_path"] = str(campaign_path)
            plan["fingerprints"]["campaign_document"] = _file(campaign_path)
        return plan
    except PolicyError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise PolicyError("plan_preparation_rejected") from None


def _timestamp(value: Any) -> datetime:
    _text(value, "approval_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except ValueError:
        raise PolicyError("approval_invalid") from None


def _approval(path: Path, digest: str, now: datetime) -> dict:
    raw = read_json(path)
    required = {"version", "approved", "plan_sha256", "approved_by", "approved_at", "expires_at"}
    if (type(raw) is not dict or set(raw) != required or type(raw["version"]) is not int
            or raw["version"] != 1 or raw["approved"] is not True
            or type(raw["plan_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", raw["plan_sha256"]) is None
            or raw["plan_sha256"] != digest):
        raise PolicyError("approval_invalid")
    _text(raw["approved_by"], "approval_invalid")
    approved_at, expires_at = _timestamp(raw["approved_at"]), _timestamp(raw["expires_at"])
    if approved_at > now or expires_at <= now or expires_at <= approved_at:
        raise PolicyError("approval_expired_or_future")
    return raw


@dataclass(frozen=True)
class ExecutionPolicy:
    plan: dict
    plan_sha256: str
    budget_usd: Decimal
    max_http_attempts: int
    model_ids: frozenset[str]
    base_url: str
    approval_id: str
    pricing: dict
    devon_root: Path
    lab_root: Path
    approval_path: Path


def validate_execution(plan: dict, *, devon_root: str | Path, cases_path: str | Path,
                       manifest_path: str | Path, pricing_path: str | Path,
                       approval_path: str | Path, base_url: str,
                       output_root: str | Path | None = None,
                       now: datetime | None = None) -> ExecutionPolicy:
    """Recompute all fingerprints and check a separate, expiring exact-plan approval."""
    try:
        if type(plan) is not dict or type(plan.get("config")) is not dict:
            raise PolicyError("plan_invalid")
        config = plan["config"]
        if type(config.get("lab_root")) is not str:
            raise PolicyError("plan_invalid")
        devon, lab = _path(devon_root), _path(config["lab_root"])
        # Resolve output paths before writing so symlinks cannot escape the lab.
        if output_root is not None:
            output = _path(output_root)
            if output.is_relative_to(devon) or not output.is_relative_to(lab / "runs"):
                raise PolicyError("output_path_rejected")
        fresh = build_plan(devon_root=devon, lab_root=lab, cases_path=cases_path,
            manifest_path=manifest_path, pricing_path=pricing_path,
            experiment=plan.get("experiment"), split=plan.get("split"), repeats=plan.get("repeats"),
            budget_usd=plan.get("budget_usd"), max_http_attempts=plan.get("max_http_attempts"),
            base_url=base_url, model_ids=plan.get("model_ids"),
            selection_path=config.get("selection_path"), campaign_path=config.get("campaign_path"))
        digest = plan_digest(plan)
        if _canonical(plan) != _canonical(fresh):
            raise PolicyError("plan_changed")
        if fresh["blocked_reasons"]:
            raise PolicyError("plan_prerequisites_missing")
        current = now or datetime.now(timezone.utc)
        if not isinstance(current, datetime) or current.tzinfo is None or current.utcoffset() is None:
            raise PolicyError("clock_invalid")
        approval_file = _path(approval_path)
        approval = _approval(approval_file, digest, current)
        return ExecutionPolicy(plan=json.loads(_canonical(plan)), plan_sha256=digest,
            budget_usd=_budget(plan["budget_usd"]), max_http_attempts=plan["max_http_attempts"],
            model_ids=frozenset(plan["model_ids"]), base_url=base_url,
            approval_id=hashlib.sha256(_canonical(approval)).hexdigest(),
            pricing=load_pricing(pricing_path), devon_root=devon, lab_root=lab,
            approval_path=approval_file)
    except PolicyError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise PolicyError("execution_preflight_rejected") from None


def claim_approval(policy: ExecutionPolicy, *, claim_root: str | Path) -> Path:
    """Recheck then exclusively consume a plan's approval once, without HTTP."""
    if type(policy) is not ExecutionPolicy:
        raise PolicyError("policy_invalid")
    target = _path(claim_root)
    expected = (policy.lab_root / "runs/.approval-claims").resolve()
    if (target != expected or target.is_relative_to(policy.devon_root)
            or not target.is_relative_to(policy.lab_root)):
        raise PolicyError("claim_path_rejected")
    config = policy.plan["config"]
    refreshed = validate_execution(policy.plan, devon_root=policy.devon_root,
        cases_path=config["cases_path"], manifest_path=config["manifest_path"],
        pricing_path=config["pricing_path"], approval_path=policy.approval_path,
        base_url=policy.base_url)
    if refreshed.approval_id != policy.approval_id:
        raise PolicyError("approval_changed")
    try:
        target.mkdir(parents=True, exist_ok=True)
        claim = target / (policy.plan_sha256 + ".json")
        with claim.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump({"version": 1, "plan_sha256": policy.plan_sha256,
                "approval_id": policy.approval_id,
                "claimed_at": datetime.now(timezone.utc).isoformat()}, stream, sort_keys=True)
            stream.write("\n")
        return claim
    except FileExistsError:
        raise PolicyError("approval_already_used") from None
    except OSError:
        raise PolicyError("approval_claim_failed") from None
