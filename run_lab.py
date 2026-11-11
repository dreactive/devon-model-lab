"""Guarded model-lab execution. Preparing a plan never calls an API."""

from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import asyncio
from contextlib import contextmanager
from dataclasses import asdict, replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values
from pydantic import SecretStr

from cost_accounting import BudgetRejected, CostBudget
from execution_policy import build_plan, claim_approval, plan_digest, validate_execution
from lab_paths import attach_devon

LAB_ROOT = Path(__file__).resolve().parent
MODEL_ENV_PREFIXES = {
    "gpt-6.1-sol": "MODEL_GPT_6_1_SOL",
    "gemini-3.8-flash": "MODEL_GEMINI_3_8_FLASH",
    "gemini-4-argon": "MODEL_GEMINI_4_ARGON",
    "claude-haiku-5-5": "MODEL_CLAUDE_HAIKU_5_5",
    "claude-sonnet-5-5": "MODEL_CLAUDE_SONNET_5_5",
    "gpt-6-luna": "MODEL_GPT_6_LUNA",
}


class BudgetStopped(BaseException):
    """Escape service executor catch-all so a halted budget stops the whole run."""


def _json(path: Path) -> dict:
    from score_eval import read_json
    value = read_json(path)
    if type(value) is not dict:
        raise ValueError("execution_document_invalid")
    return value


def _redact_provider_json(value, api_key: str):
    """Keep provider output evidence while excluding credentials and auth fields."""
    secret_names = {"authorization", "api_key", "api-key", "apikey", "password",
                    "access_token", "refresh_token", "client_secret", "secret_key"}
    def clean(item):
        if type(item) is str:
            return item.replace(api_key, "[REDACTED]") if api_key else item
        if type(item) is list:
            return [clean(child) for child in item]
        if type(item) is dict:
            return {clean(name): "[REDACTED]" if name.casefold() in secret_names else clean(child)
                    for name, child in item.items()}
        return item
    return clean(value)


def _credentials(path: Path, lab_root: Path, *, model_id: str | None = None) -> tuple[str, str]:
    expected = lab_root.resolve() / ".env"
    if path.resolve() != expected or not path.is_file():
        raise ValueError("local_env_required")
    values = dotenv_values(path, interpolate=False)
    prefix = MODEL_ENV_PREFIXES.get(model_id)
    def configured(name):
        value = values.get(name)
        return value.strip() if value and value.strip() else None
    key = (configured(prefix + "_API_KEY") if prefix else None) or configured("OPENAI_API_KEY")
    endpoint = (configured(prefix + "_BASE_URL") if prefix else None) or configured("LLM_BASE_URL")
    if not key or not key.strip() or not endpoint or not endpoint.strip():
        raise ValueError("local_credentials_required")
    endpoint = endpoint.strip().rstrip("/")
    try:
        parsed = urlsplit(endpoint)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host == "mlapi.run" or host.endswith(".mlapi.run"):
            # Elice's configured value is the versioned base, not a method URL.
            # Reject locally so a missing /v1 cannot consume a paid attempt.
            if (parsed.scheme != "https" or not parsed.path.endswith("/v1")
                    or parsed.username is not None or parsed.password is not None
                    or "?" in endpoint or "#" in endpoint
                    or any(character.isspace() or ord(character) < 32 for character in endpoint)):
                raise ValueError
            _ = parsed.port
    except ValueError:
        # URL parser errors can contain configuration text; export only a code.
        raise ValueError("elice_endpoint_invalid") from None
    return key.strip(), endpoint


def _engine_args(config: dict, *, execute: bool, checkpoint=None) -> argparse.Namespace:
    return argparse.Namespace(
        cases=Path(config["cases_path"]), manifest=Path(config["manifest_path"]),
        split=config.get("split", "dev"), approved_only=False, execute=execute,
        max_model_attempts=config.get("max_http_attempts") if execute else None,
        llm_judge=False, max_judge_attempts=None, diagnostic_judge=False,
        calibrate_judge_only=False, rejudge_results=None, judge_prompt_version=None,
        judge_prompt=None, env_file=None, grader=None, _checkpoint=checkpoint,
    )


async def _precheck(plan: dict, devon: Path) -> None:
    """Reject input errors before consuming an approval or opening a transport."""
    config = {**plan["config"], "split": plan["split"]}
    if plan["experiment"] == "A":
        from scripts import run_ai_evaluation as engine
        result = await dry_run_question(config)
        check = result["summary"]["automatic_checks"]["input_contract"]
        if (check["failed"] or not check["passed"] or not result.get("cases")
                or any(row.get("status") != "validated_only" for row in result["cases"])):
            raise ValueError("input_precheck_rejected")
    else:
        import score_eval
        prompt, limits, _ = score_eval.load_manifest(Path(config["manifest_path"]), devon)
        cases = _select_cases(config, score_eval.load_inputs(Path(config["cases_path"])), "B", model_id=prompt.model)
        selected = [case for case in cases if plan["split"] == "all" or case.envelope["control"]["split"] == plan["split"]]
        if not selected:
            raise ValueError("input_precheck_rejected")
        for case in selected:
            row = await score_eval.validate_case(case, Path(config["cases_path"]), prompt, limits)
            if row["status"] != "validated_only":
                raise ValueError("input_precheck_rejected")


@contextmanager
def _bound_case_selection(engine, config: dict):
    """Keep original full-root loading/provenance checks before subset filtering."""
    original = engine.load_cases
    if config.get("selection_path") is not None:
        choice = _resolve_selection(config, "A")
        prompts, _, _ = engine.load_manifest(Path(config["manifest_path"]))
        if prompts["director"].model not in choice.model_ids:
            raise ValueError("selection_model_mismatch")

    def selected(*args, **kwargs):
        return _select_cases(config, original(*args, **kwargs), "A")

    engine.load_cases = selected
    try:
        yield
    finally:
        engine.load_cases = original


def _resolve_selection(config: dict, experiment: str):
    if config.get("selection_path") is None:
        return None
    from case_selection import resolve_selection
    return resolve_selection(Path(config["selection_path"]),
        lab_root=Path(config.get("lab_root", LAB_ROOT)), cases_path=Path(config["cases_path"]),
        experiment=experiment, split=config.get("split", "dev"))


def _select_cases(config: dict, cases, experiment: str, *, model_id=None):
    selection = _resolve_selection(config, experiment)
    if selection is None:
        return cases
    from case_selection import filter_cases
    if model_id is not None and model_id not in selection.model_ids:
        raise ValueError("selection_model_mismatch")
    return filter_cases(cases, selection)


@contextmanager
def _bound_question_executor(engine, root: Path):
    """Add lab recovery feedback at the original executor seam, without file edits."""
    from question_runtime import RecoveryExecutor
    original = engine.ServiceExecutor

    def bound(*args, **kwargs):
        return RecoveryExecutor(root, *args, **kwargs)

    engine.ServiceExecutor = bound
    try:
        yield
    finally:
        engine.ServiceExecutor = original


async def dry_run_question(config: dict) -> dict:
    """Use the same recovery binding in offline preflight and paid execution."""
    from scripts import run_ai_evaluation as engine
    with _bound_question_executor(engine, Path(config["cases_path"])), _bound_case_selection(engine, config):
        return await engine.execute(_engine_args(config, execute=False))


def _budget_factory(original_class, http, cost_budget, guarded):
    class BoundBudget:
        def __init__(self, maximum, settings, *, http_client=None):
            if http_client is not None:
                raise ValueError("unguarded_client_rejected")
            self.inner = original_class(maximum, settings, http_client=http)

        @property
        def remaining(self):
            return self.inner.remaining

        def factory(self):
            invoke_original = self.inner.factory()

            async def invoke(request, validator):
                if guarded.snapshot()["halted"]:
                    raise BudgetStopped()
                try:
                    result = await invoke_original(request, validator)
                except BudgetRejected:
                    raise BudgetStopped() from None
                if guarded.snapshot()["halted"] or cost_budget.to_dict()["halted"]:
                    raise BudgetStopped()
                return result
            return invoke
    return BoundBudget


@contextmanager
def _bound_engine(engine, budget_class, settings):
    """Process-local injection; original DEVON functions and files stay intact."""
    old_budget, old_settings, old_get = engine.ModelAttemptBudget, engine.Settings, engine.get_settings
    wrapper = SimpleNamespace(require_llm=lambda: settings)
    engine.ModelAttemptBudget = budget_class
    engine.Settings = lambda **kwargs: wrapper
    engine.get_settings = lambda: wrapper
    try:
        yield
    finally:
        engine.ModelAttemptBudget, engine.Settings, engine.get_settings = old_budget, old_settings, old_get


async def _score_execute(policy, budget_class, settings, checkpoint):
    from devon_ai import contracts as c
    from devon_ai.llm_tasks import report, report_score
    import score_eval

    config, plan = policy.plan["config"], policy.plan
    root = Path(config["cases_path"])
    prompt, limits, metadata = score_eval.load_manifest(Path(config["manifest_path"]), policy.devon_root)
    result = {"experiment": "B", "mode": "execute", "manifest": metadata, "cases": [],
              "summary": {"total_cases": 0, "quality_denominator": 0, "quality_evaluation": "diagnostic_only"}}
    factory = budget_class(policy.max_http_attempts, settings)
    cases = _select_cases({**config, "split": plan["split"]}, score_eval.load_inputs(root), "B", model_id=prompt.model)
    selected = [case for case in cases if plan["split"] == "all" or case.envelope["control"]["split"] == plan["split"]]
    for _ in range(plan["repeats"]):
        for case in selected:
            result["in_progress_case"] = case.envelope["case_id"]
            await checkpoint(result)
            turns, rubric, report_input = report._build_inputs(case.envelope["payload"]["service_input"])
            scored = await report_score.judge_scores(
                turns, rubric=rubric, prompt=prompt, limits=limits, model_call=factory.factory(),
                supplemental_sources=report_input.supplemental_sources, limitations=report_input.limitations,
                evidence=report_input.evidence, tool_results=report_input.tool_results, source_notes=report_input.source_notes,
            )
            attempts = [asdict(item) for item in scored.attempts]
            for item in attempts:
                item.pop("raw_output", None)
            row = {"case_id": case.envelope["case_id"], "kind": "report", "attempts": attempts,
                   "status": "succeeded" if scored.data is not None and scored.failure is None else "failed",
                   "output": asdict(scored.data.data) if scored.data is not None else None,
                   "review_status": "unreviewed", "quality": "excluded_unreviewed",
                   "failure": asdict(scored.failure) if scored.failure is not None else None}
            result["cases"].append(row)
            result["summary"]["total_cases"] += 1
            result["in_progress_case"] = None
            await checkpoint(result)
    return result


async def execute_approved_plan(plan_path: Path, approval_path: Path, env_path: Path,
                                output_path: Path, *, delegate=None, campaign_context=None) -> dict:
    """The only paid-capable lab entry; tests inject MockTransport through delegate."""
    if not approval_path.is_file():
        raise ValueError("approval_required")
    plan = _json(plan_path)
    if plan.get("config", {}).get("campaign_path") is not None:
        if campaign_context is None:
            raise ValueError("campaign_context_required")
        from campaign_runtime import CampaignContext
        if not isinstance(campaign_context, CampaignContext):
            raise ValueError("campaign_context_required")
    elif campaign_context is not None:
        raise ValueError("campaign_context_not_expected")
    lab_root = Path(plan["config"]["lab_root"]).resolve()
    if lab_root != LAB_ROOT.resolve():
        raise ValueError("foreign_lab_plan_rejected")
    devon = attach_devon(Path(plan["config"]["devon_root"]))
    output_path = output_path.resolve()
    if output_path.is_relative_to(devon) or not output_path.is_relative_to(lab_root) or output_path.exists():
        raise ValueError("output_rejected")
    executable_models = plan.get("model_ids")
    if (type(executable_models) is not list or len(executable_models) != 1
            or type(executable_models[0]) is not str or not executable_models[0]):
        raise ValueError("executable_models_mismatch")
    key, endpoint = _credentials(env_path, lab_root, model_id=executable_models[0])
    config = plan["config"]
    policy = validate_execution(plan, devon_root=devon,
        cases_path=Path(config["cases_path"]), manifest_path=Path(config["manifest_path"]),
        pricing_path=Path(config["pricing_path"]), approval_path=approval_path,
        base_url=endpoint, output_root=output_path.parent)
    if campaign_context is not None:
        campaign_context.validate(policy)
    if plan["experiment"] == "A" and plan["repeats"] != 1:
        raise ValueError("a_repeats_require_separate_plan")
    await _precheck(plan, devon)
    # Validate again after prechecks so changed inputs cannot retain approval.
    policy = validate_execution(plan, devon_root=devon, cases_path=Path(config["cases_path"]),
        manifest_path=Path(config["manifest_path"]), pricing_path=Path(config["pricing_path"]),
        approval_path=approval_path, base_url=endpoint, output_root=output_path.parent)
    if campaign_context is not None:
        campaign_context.validate(policy)
    from scripts import run_ai_evaluation as engine
    from scripts.evaluation_output import RunOutput
    from app.core.config import LLMSettings
    from adapters.guarded_transport import GuardedTransport

    prompts, limits, metadata = engine.load_manifest(Path(config["manifest_path"]))
    task = "director" if plan["experiment"] == "A" else "report_score"
    limits = replace(limits, **metadata.get("task_limits", {}).get(task, {}))
    allowed_limits = {model: {"max_input_bytes": limits.max_input_bytes,
        "max_output_tokens": limits.max_output_tokens, "max_response_bytes": limits.max_response_bytes}
        for model in policy.model_ids}
    settings = LLMSettings(openai_api_key=SecretStr(key), llm_base_url=endpoint,
        llm_default_model=prompts[task].model, llm_timeout_seconds=limits.timeout_seconds,
        llm_max_output_tokens=limits.max_output_tokens, llm_max_input_bytes=limits.max_input_bytes,
        llm_max_response_bytes=limits.max_response_bytes,
        llm_reasoning_effort=limits.reasoning_effort, llm_stream=limits.stream)
    budget = CostBudget(policy.budget_usd, policy.max_http_attempts, approval_id=policy.approval_id)
    # Claim is single-use, and happens only after all configuration/input checks.
    claim_approval(policy, claim_root=lab_root / "runs/.approval-claims")
    output = RunOutput(output_path)
    events, raw_artifacts = [], []
    output.latest.update(experiment=plan["experiment"], mode="execute", approval_plan_sha256=policy.plan_sha256)

    def audit(event):
        event = _redact_provider_json(event, key)
        events.append(event)
        snapshot = {**budget.to_dict(), "transport_integration": "guarded_http_transport"}
        output.save(_redact_provider_json({**output.latest, "cost_budget": snapshot, "cost_audit": events}, key), "running")
        if campaign_context is not None:
            campaign_context.audit_callback({**event, "plan_sha256": policy.plan_sha256,
                "result_path": output_path.relative_to(lab_root).as_posix()})

    def raw_response(value):
        cleaned = _redact_provider_json(value, key)
        raw_root = output_path.parent / (output_path.stem + "-raw")
        raw_root.mkdir(parents=True, exist_ok=True)
        path = raw_root / f"response-{len(raw_artifacts)+1:04}.json"
        encoded = (json.dumps(cleaned, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
        with path.open("xb") as stream:
            stream.write(encoded)
        raw_artifacts.append({"path": path.relative_to(lab_root).as_posix(),
            "sha256": hashlib.sha256(encoded).hexdigest()})

    transport_args = dict(budget=budget, pricing=policy.pricing, allowed_models=set(policy.model_ids),
        allowed_endpoint=endpoint + "/responses", allowed_limits=allowed_limits, audit_callback=audit)
    network = delegate if delegate is not None else httpx.AsyncHTTPTransport(retries=0)
    if campaign_context is not None:
        from adapters.elice_transport import EliceTransport
        guarded = EliceTransport(network, global_budget=campaign_context.budget,
            wire_protocol=campaign_context.wire_protocol_for(executable_models[0]),
            raw_response_callback=raw_response, **transport_args)
    else:
        guarded = GuardedTransport(network, **transport_args)
    http = httpx.AsyncClient(transport=guarded, follow_redirects=False, trust_env=False)
    budget_class = _budget_factory(engine.ModelAttemptBudget, http, budget, guarded)

    async def checkpoint(report):
        await output.checkpoint(_redact_provider_json({**report, "approval_plan_sha256": policy.plan_sha256,
            "cost_budget": {**budget.to_dict(), "transport_integration": "guarded_http_transport"},
            "cost_audit": list(events), "raw_response_artifacts": list(raw_artifacts)}, key))

    state = "completed"
    try:
        if plan["experiment"] == "A":
            args = _engine_args({**config, "split": plan["split"], "max_http_attempts": policy.max_http_attempts},
                                execute=True, checkpoint=checkpoint)
            with _bound_engine(engine, budget_class, settings), _bound_question_executor(engine, Path(config["cases_path"])), _bound_case_selection(engine, {**config, "split": plan["split"]}):
                result = await engine.execute(args)
        else:
            result = await _score_execute(policy, budget_class, settings, checkpoint)
    except (BudgetStopped, BudgetRejected):
        state, result = "budget_stopped", dict(output.latest)
        result["run_error"] = {"code": guarded.snapshot().get("halt_reason") or "budget_rejected"}
    except (KeyboardInterrupt, asyncio.CancelledError):
        state, result = "interrupted", dict(output.latest)
        result["run_error"] = {"code": "run_interrupted"}
        if campaign_context is not None:
            campaign_context.budget.halt("campaign_interrupted")
    except Exception:
        state, result = "failed", dict(output.latest)
        result["run_error"] = {"code": "guarded_execution_failed"}
        if campaign_context is not None:
            campaign_context.budget.halt("campaign_job_failed")
    finally:
        try:
            await http.aclose()
        except BudgetRejected:
            state = "budget_stopped"
            result["run_error"] = {"code": "transport_shutdown_failed"}
        except BaseException as error:
            state = "interrupted" if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else "failed"
            result["run_error"] = {"code": "transport_shutdown_failed"}
    snapshot = guarded.snapshot()
    result.update(experiment=plan["experiment"], approval_plan_sha256=policy.plan_sha256,
        cost_budget={**budget.to_dict(), "halted": snapshot["halted"], "halt_reason": snapshot["halt_reason"],
                     "transport_integration": "guarded_http_transport"},
        cost_audit=events, guarded_transport=snapshot, raw_response_artifacts=raw_artifacts)
    if campaign_context is not None:
        result["cost_budget"]["accounting_basis"] = "conservative_cost_upper_bound"
        result["campaign_budget"] = {**campaign_context.budget.to_dict(),
            "accounting_basis": "conservative_cost_upper_bound"}
    output.save(_redact_provider_json(result, key), state)
    return output.latest


def technical_exit_code(result: dict) -> int:
    if result.get("run_state") != "completed":
        return 1
    if not result.get("cases") or any(row.get("status") in {"failed", "rejected"} for row in result["cases"]):
        return 1
    checks = result.get("summary", {}).get("automatic_checks", {})
    return int(any(value.get("failed", 0) for value in checks.values() if type(value) is dict))


def parser():
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="Offline plan only (default).")
    mode.add_argument("--execute", action="store_true", help="Requires priced, budgeted, pinned single-use approval.")
    result.add_argument("--experiment", choices=("A", "B"))
    result.add_argument("--devon-root", type=Path)
    result.add_argument("--cases", type=Path)
    result.add_argument("--manifest", type=Path, default=LAB_ROOT / "manifests/baseline.json")
    result.add_argument("--pricing", type=Path, default=LAB_ROOT / "pricing.yaml")
    result.add_argument("--split", choices=("all", "dev", "holdout"), default="dev")
    result.add_argument("--selection", dest="selection_path", type=Path,
                        help="Pinned dev case/version selection; same file for all candidate models.")
    result.add_argument("--base-url")
    result.add_argument("--budget-usd", type=Decimal)
    result.add_argument("--max-http-attempts", type=int)
    result.add_argument("--repeats", type=int, default=1)
    result.add_argument("--plan", type=Path)
    result.add_argument("--approval", type=Path)
    result.add_argument("--env-file", type=Path, default=LAB_ROOT / ".env")
    result.add_argument("--output", type=Path, required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.execute:
            if args.plan is None or args.approval is None:
                raise ValueError("plan_and_approval_required")
            result = asyncio.run(execute_approved_plan(args.plan, args.approval, args.env_file, args.output))
            print(json.dumps({"run_state": result["run_state"], "cost_budget": result["cost_budget"]}))
            return technical_exit_code(result)
        if args.experiment is None or args.cases is None or args.base_url is None:
            raise ValueError("prepare_arguments_required")
        devon = attach_devon(args.devon_root)
        if args.output.resolve().is_relative_to(devon) or not args.output.resolve().is_relative_to(LAB_ROOT):
            raise ValueError("output_rejected")
        plan = build_plan(devon_root=devon, lab_root=LAB_ROOT, cases_path=args.cases,
            manifest_path=args.manifest, pricing_path=args.pricing, experiment=args.experiment,
            split=args.split, repeats=args.repeats, base_url=args.base_url,
            budget_usd=args.budget_usd, max_http_attempts=args.max_http_attempts,
            selection_path=args.selection_path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps({"mode": "prepare", "plan_sha256": plan_digest(plan),
                          "max_http_attempts": plan["max_http_attempts"], "budget_usd": plan["budget_usd"],
                          "expected_lower_usd": plan["expected_lower_usd"], "expected_upper_usd": plan["expected_upper_usd"],
                          "estimated_upper_exceeds_budget": plan["estimated_upper_exceeds_budget"],
                          "blocked_reasons": plan["blocked_reasons"], "api_calls": 0}))
        return 0
    except Exception:
        print(json.dumps({"status": "blocked", "error": "execution_rejected",
                          "api_calls": None if args.execute else 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
