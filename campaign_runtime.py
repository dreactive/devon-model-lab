"""Pinned six-model campaign with one shared, durable upper-cost budget.

No network client is constructed here. Real model calls are delegated only after
all eighteen original service prechecks and approvals have passed. Tests inject
local executors; only the root operator runs the real entry point.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode=True

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Callable

from cost_accounting import CostBudget, BudgetRejected
from execution_policy import PolicyError, build_plan, plan_digest, read_json, validate_execution

LAB_ROOT=Path(__file__).resolve().parent
MODELS=('gpt-6.1-sol','gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5','gpt-6-luna')
SELECTION='selections/dev-30pct-v1.json'
SELECTION_SHA256='f3dc03a866c9e5d299ff5f6860252ef763ecaeb879d80f1d3f0c22b18aa4bfd5'
ROOTS=(('A','cases/question/benchmark-v1',22,11),('B','cases/answer/main-v1',8,4),('B','cases/answer/legacy-na-v1',2,1))
BASE_RATES={'gpt-6.1-sol':('2','10'),'gemini-3.8-flash':('.75','3.75'),'gemini-4-argon':('2','10'),
            'claude-haiku-5-5':('.10','.50'),'claude-sonnet-5-5':('2','10'),'gpt-6-luna':('.10','.50')}
ATTACHMENT=Path('C:/Users/dreac/.codex/attachments/e31e678c-2597-49bf-b01d-0f234bfdb547/붙여넣은 텍스트.txt')
ATTACHMENT_SHA256='b192518d816ae1568fe75eb28ba70091bc90d5e76caae4940cfe47352f35e095'
NONSTREAM_CAP_MESSAGE=('max_output_tokens 4096 exceeds the 2000-token ceiling this proxy holds a NON-STREAMING reply to: '
    'the answer is invisible until it finishes and the gateway kills a long one mid-generation, so a larger '
    'budget would buy a timeout rather than a longer answer. Send stream=true for the full length, or lower '
    'max_output_tokens to 2000 or less.')
UNSUPPORTED_TEXT_MESSAGE=('Unsupported parameter(s) for /v1/responses on this model: text. They cannot be honoured here '
    'and are rejected rather than ignored — remove them from the request.')
WIRE_PROTOCOL_BY_MODEL={model:('responses' if model in {'gpt-6.1-sol','gpt-6-luna'} else 'chat_completions')
    for model in MODELS}
PREFIX_JOB_IDS=[f'gpt-6.1-sol-{number}' for number in (1,2,3)]
REMAINING_JOB_IDS=[f'{model}-{number}' for model in ('gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5',
    'gpt-6-luna','claude-sonnet-5-5') for number in (1,2,3)]
TERMINAL_PREFIX_JOB_IDS=PREFIX_JOB_IDS+[f'gemini-3.8-flash-{number}' for number in (1,2,3)]+['gemini-4-argon-1']
TERMINAL_REMAINING_JOB_IDS=['gemini-4-argon-2','gemini-4-argon-3']+[f'{model}-{number}' for model in
    ('claude-haiku-5-5','gpt-6-luna','claude-sonnet-5-5') for number in (1,2,3)]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _amount(value) -> Decimal:
    if type(value) is not str:
        raise ValueError('campaign_budget_invalid')
    try:
        amount=Decimal(value)
    except InvalidOperation:
        raise ValueError('campaign_budget_invalid') from None
    if not amount.is_finite() or amount<=0:
        raise ValueError('campaign_budget_invalid')
    return amount


def _write_new(path: Path,value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def _atomic(path: Path,value) -> None:
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary,path)


def _inside(path: Path,root: Path,code='campaign_path_rejected') -> Path:
    try:
        path=Path(path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(code)
        return path
    except (OSError,RuntimeError,TypeError):
        raise ValueError(code) from None


def validate_campaign_config(value: dict) -> dict:
    """Freeze the approved cohort, allocations, retry caps and no-extra-call scope."""
    try:
        if (type(value) is not dict or type(value.get('version')) is not int or value.get('version')!=1
                or value.get('campaign_id')!='dev-30pct-10usd'
                or value.get('selection')!=SELECTION or _amount(value.get('budget_usd_total'))!=Decimal('10')
                or type(value.get('max_http_attempts_total')) is not int or value['max_http_attempts_total']!=192
                or type(value.get('repeats')) is not int or value['repeats']!=1
                or type(value.get('model_count')) is not int or value.get('model_count')!=6
                or type(value.get('selected_inputs_per_model')) is not int or value.get('selected_inputs_per_model')!=16
                or value.get('scope_authorized_in_chat') is not True
                or value.get('stop_entire_campaign_on_unknown_usage') is not True
                or value.get('stop_on_budget_exhaustion') is not True
                or type(value.get('extra_smoke')) is not int or value.get('extra_smoke')!=0
                or value.get('semantic_judge') is not False
                or value.get('review_status')!='unreviewed' or type(value.get('models')) is not list
                or tuple(row.get('model_id') for row in value['models'])!=MODELS):
            raise ValueError('campaign_scope_invalid')
        total=Decimal(0)
        attempts=0
        for model in value['models']:
            if (set(model)!={'model_id','manifest','budget_usd','jobs'}
                    or model['manifest']!=f"manifests/elice-30pct/{model['model_id']}.json"
                    or type(model['jobs']) is not list or len(model['jobs'])!=3):
                raise ValueError('campaign_scope_invalid')
            cap=_amount(model['budget_usd'])
            subtotal=Decimal(0)
            for row,(kind,relative,count,_) in zip(model['jobs'],ROOTS,strict=True):
                if (type(row) is not dict or set(row)!={'experiment','cases_root','max_http_attempts','budget_usd'}
                        or row['experiment']!=kind or row['cases_root']!=relative
                        or type(row['max_http_attempts']) is not int or row['max_http_attempts']!=count):
                    raise ValueError('campaign_scope_invalid')
                subtotal+=_amount(row['budget_usd'])
                attempts+=count
            if subtotal!=cap:
                raise ValueError('campaign_budget_invalid')
            total+=cap
        if total!=Decimal('10') or attempts!=192:
            raise ValueError('campaign_budget_invalid')
        return deepcopy(value)
    except (KeyError,TypeError,AttributeError):
        raise ValueError('campaign_scope_invalid') from None


@dataclass(frozen=True)
class CampaignContext:
    budget: CostBudget
    campaign_path: Path
    campaign_sha256: str
    plan_sha256s: frozenset[str]
    audit_callback: Callable[[dict],None]
    continuation: dict|None=None

    def wire_protocol_for(self,model_id:str) -> str:
        if model_id not in MODELS:
            raise ValueError('campaign_model_invalid')
        if _recovery_phase(self.continuation)<3:
            return 'responses'
        _verify_continuation(self.continuation,Path(self.campaign_path).resolve().parent.parent)
        return self.continuation['wire_protocol_by_model'][model_id]

    def validate(self,policy) -> None:
        root=Path(policy.lab_root).resolve()
        if self.continuation is not None:
            _verify_continuation(self.continuation,root)
        amount,attempts=_active_allowance(self.continuation)
        if (type(self.budget) is not CostBudget or self.budget.amount_usd!=amount
                or self.budget.max_attempts!=attempts or not callable(self.audit_callback)
                or policy.plan_sha256 not in self.plan_sha256s
                or plan_digest(policy.plan)!=policy.plan_sha256):
            raise ValueError('campaign_context_invalid')
        campaign=_inside(self.campaign_path,root/'campaigns')
        if (str(campaign)!=policy.plan['config'].get('campaign_path')
                or file_sha256(campaign)!=self.campaign_sha256
                or policy.plan.get('split')!='dev' or policy.plan.get('repeats')!=1):
            raise ValueError('campaign_context_changed')
        config=validate_campaign_config(read_json(campaign))
        selection=root/SELECTION
        if (policy.plan['config'].get('selection_path')!=str(selection.resolve())
                or file_sha256(selection)!=SELECTION_SHA256):
            raise ValueError('campaign_selection_changed')
        models=policy.plan.get('model_ids')
        if type(models) is not list or len(models)!=1 or models[0] not in MODELS:
            raise ValueError('campaign_model_invalid')
        if _recovery_phase(self.continuation)>=3 and models[0]=='gpt-6.1-sol':
            raise ValueError('campaign_job_reused')
        model=next(row for row in config['models'] if row['model_id']==models[0])
        relative=Path(policy.plan['config']['cases_path']).resolve().relative_to(root).as_posix()
        if _recovery_phase(self.continuation)>=3:
            number=next((number for number,(_,path,_,_) in enumerate(ROOTS,1) if path==relative),None)
            if f'{models[0]}-{number}' in self.continuation['reused_completed_job_ids']:
                raise ValueError('campaign_job_reused')
        job=next((row for row in model['jobs'] if row['cases_root']==relative),None)
        if job is not None:
            job=_continuation_job(models[0],job,self.continuation)
        if (job is None or policy.plan['experiment']!=job['experiment']
                or policy.budget_usd!=_amount(job['budget_usd'])
                or policy.max_http_attempts!=job['max_http_attempts']):
            raise ValueError('campaign_job_invalid')
        if (_recovery_phase(self.continuation)>=2 and
                (policy.plan['limits']['max_output_tokens']!=2000 or policy.plan['limits']['stream'] is not False)):
            raise ValueError('continuation_output_limit_changed')
        if self.budget.to_dict()['halted']:
            raise BudgetRejected('campaign_budget_halted')


def prepare_campaign(devon_root: Path,campaign_path: Path,output_dir: Path,*,
                     env_path: Path|None=None,lab_root: Path|None=None,
                     _continuation: dict|None=None) -> dict:
    """Prepare a new one-shot, content-pinned bundle; no model or HTTP calls."""
    lab=Path(lab_root or LAB_ROOT).resolve()
    devon=Path(devon_root).resolve()
    campaign=_inside(campaign_path,lab/'campaigns')
    destination=_inside(output_dir,lab/'runs')
    if destination.exists() or destination.is_relative_to(devon):
        raise ValueError('campaign_output_exists_or_invalid')
    config=validate_campaign_config(read_json(campaign))
    if _continuation is not None:
        _verify_continuation(_continuation,lab)
    selection=lab/SELECTION
    if file_sha256(selection)!=SELECTION_SHA256:
        raise ValueError('campaign_selection_changed')
    from case_selection import resolve_selection
    from run_lab import _credentials
    env=Path(env_path or lab/'.env')
    endpoints={}
    # Only non-sensitive destination hashes are persisted, never endpoint/key strings.
    for model in MODELS:
        _,endpoints[model]=_credentials(env,lab,model_id=model)
    for kind,relative,_,expected in ROOTS:
        selected=resolve_selection(selection,lab_root=lab,cases_path=lab/relative,experiment=kind,split='dev')
        if len(selected.case_keys)!=expected or selected.model_ids!=MODELS:
            raise ValueError('campaign_selection_changed')
    if not ATTACHMENT.is_file() or file_sha256(ATTACHMENT)!=ATTACHMENT_SHA256:
        raise ValueError('campaign_price_source_changed')
    source_manifests={}
    for model in config['models']:
        path=_inside(lab/model['manifest'],lab/'manifests')
        raw=read_json(path)
        if any(row.get('model')!=model['model_id'] for row in raw['prompts']):
            raise ValueError('campaign_manifest_model_invalid')
        manifest=deepcopy(raw)
        manifest['limits']['max_input_bytes']=65536
        output_limit=2000 if _recovery_phase(_continuation)>=2 else 4096
        manifest['limits']['max_output_tokens']=output_limit
        manifest['limits']['stream']=False
        for overrides in manifest.get('task_limits',{}).values():
            if 'max_input_bytes' in overrides:overrides['max_input_bytes']=65536
            if 'max_output_tokens' in overrides:overrides['max_output_tokens']=output_limit
            if 'stream' in overrides:overrides['stream']=False
        source_manifests[model['model_id']]=manifest
    destination.mkdir(parents=True,exist_ok=False)
    pricing={'version':1,'currency':'USD','unit':1000000,'models':{}}
    for model,(input_rate,output_rate) in BASE_RATES.items():
        pricing['models'][model]={'input_usd_per_million':input_rate,'output_usd_per_million':output_rate,
            'cached_input_usd_per_million':None,'reasoning_output_usd_per_million':None,
            'source_url':'https://kakaotechcampus.elice.io/cloud/mlapi/model-libraries',
            'checked_at':'2026-11-11','price_version':'user-supplied-html-sha256-'+ATTACHMENT_SHA256,
            'source_path':str(ATTACHMENT),'billing_basis':'Elice billing bounds in elice_billing.py; not base-only invoice accounting'}
    price_path=destination/'pricing.yaml'
    _write_new(price_path,pricing) # JSON is a strict subset of YAML.
    for model,manifest in source_manifests.items():
        _write_new(destination/'manifests'/f'{model}.json',manifest)
    now=datetime.now(timezone.utc)
    jobs=[]
    for model in config['models']:
        for number,job in enumerate(model['jobs'],1):
            job=_continuation_job(model['model_id'],job,_continuation)
            identifier=f"{model['model_id']}-{number}"
            manifest=destination/'manifests'/f"{model['model_id']}.json"
            plan=build_plan(devon_root=devon,lab_root=lab,cases_path=lab/job['cases_root'],
                manifest_path=manifest,pricing_path=price_path,experiment=job['experiment'],
                split='dev',repeats=1,budget_usd=job['budget_usd'],max_http_attempts=job['max_http_attempts'],
                base_url=endpoints[model['model_id']],selection_path=selection,campaign_path=campaign)
            if plan['blocked_reasons']:
                raise ValueError('campaign_plan_prerequisites_missing')
            digest=plan_digest(plan)
            plan_relative=f'plans/{identifier}.json'
            approval_relative=f'approvals/{identifier}.json'
            _write_new(destination/plan_relative,plan)
            _write_new(destination/approval_relative,{'version':1,'approved':True,'plan_sha256':digest,
                'approved_by':'user explicit chat authorization: same16cases,6models,USD10 total',
                'approved_at':now.isoformat(),'expires_at':(now+timedelta(hours=24)).isoformat()})
            jobs.append({'job_id':identifier,'model_id':model['model_id'],'experiment':job['experiment'],
                'cases_root':job['cases_root'],'budget_usd':job['budget_usd'],'max_http_attempts':job['max_http_attempts'],
                'plan_path':plan_relative,'approval_path':approval_relative,'plan_sha256':digest,
                'output_path':f'results/{identifier}.json','expected_cases':len(plan['selected_case_ids'])})
    bundle={'version':1,'campaign_id':config['campaign_id'],'lab_root':str(lab),'devon_root':str(devon),
        'campaign_path':str(campaign),'campaign_sha256':file_sha256(campaign),'selection_path':str(selection.resolve()),
        'selection_sha256':SELECTION_SHA256,'budget_usd_total':'10.00','max_http_attempts_total':192,
        'review_status':'unreviewed','quality_evaluation':'diagnostic_only','created_at':now.isoformat(),
        'billing_basis':'upper-bound debits; exact cost kept separately when known','jobs':jobs}
    if _continuation is not None:
        active_amount,active_attempts=_active_allowance(_continuation)
        bundle.update(continuation=deepcopy(_continuation),active_budget_usd=format(active_amount,'f'),
            active_max_http_attempts=active_attempts,prior_first_case_retry=True)
        if _recovery_phase(_continuation)>=2:
            bundle['max_output_tokens_all_models']=2000
        if _recovery_phase(_continuation)>=3:
            bundle['reused_completed_job_ids']=deepcopy(_continuation['reused_completed_job_ids'])
            bundle['execution_job_ids']=deepcopy(_continuation['execution_job_ids'])
    _write_new(destination/'bundle.json',bundle)
    return bundle


def _bundle(path: Path,lab: Path) -> tuple[dict,Path]:
    path=_inside(path,lab/'runs')
    bundle=read_json(path)
    if (type(bundle) is not dict or bundle.get('version')!=1 or bundle.get('lab_root')!=str(lab)
            or bundle.get('campaign_id')!='dev-30pct-10usd' or bundle.get('budget_usd_total')!='10.00'
            or bundle.get('max_http_attempts_total')!=192 or bundle.get('selection_sha256')!=SELECTION_SHA256
            or bundle.get('review_status')!='unreviewed' or type(bundle.get('jobs')) is not list
            or len(bundle['jobs'])!=18 or len({row['job_id'] for row in bundle['jobs']})!=18):
        raise ValueError('campaign_bundle_invalid')
    campaign=_inside(bundle['campaign_path'],lab/'campaigns')
    config=validate_campaign_config(read_json(campaign))
    if file_sha256(campaign)!=bundle['campaign_sha256'] or file_sha256(lab/SELECTION)!=SELECTION_SHA256:
        raise ValueError('campaign_bundle_changed')
    continuation=bundle.get('continuation')
    if continuation is not None:
        _verify_continuation(continuation,lab)
    active_amount,active_attempts=_active_allowance(continuation)
    runnable=bundle['jobs']
    if _recovery_phase(continuation)>=3:
        if (bundle.get('reused_completed_job_ids')!=continuation['reused_completed_job_ids']
                or bundle.get('execution_job_ids')!=continuation['execution_job_ids']):
            raise ValueError('campaign_bundle_scope_changed')
        runnable=[row for row in bundle['jobs'] if row['job_id'] in continuation['execution_job_ids']]
        expected_amount,expected_attempts={3:(Decimal('7.47580725'),159),4:(Decimal('4.9875'),106)}[_recovery_phase(continuation)]
        if (sum(_amount(row['budget_usd']) for row in runnable)!=expected_amount
                or sum(row['max_http_attempts'] for row in runnable)!=expected_attempts
                or sum(_amount(row['budget_usd']) for row in runnable)>active_amount
                or sum(row['max_http_attempts'] for row in runnable)>active_attempts):
            raise ValueError('campaign_bundle_invalid')
    elif (sum(_amount(row['budget_usd']) for row in runnable)!=active_amount
            or sum(row['max_http_attempts'] for row in runnable)!=active_attempts):
        raise ValueError('campaign_bundle_invalid')
    if sum(row['expected_cases'] for row in bundle['jobs'])!=96:
        raise ValueError('campaign_bundle_invalid')
    expected={(model,kind,relative) for model in MODELS for kind,relative,_,_ in ROOTS}
    actual=[(row['model_id'],row['experiment'],row['cases_root']) for row in bundle['jobs']]
    if len(set(actual))!=18 or set(actual)!=expected:
        raise ValueError('campaign_bundle_scope_changed')
    expected_sizes={relative:count for _,relative,_,count in ROOTS}
    for key in ('plan_path','approval_path','output_path','plan_sha256'):
        values=[row[key] for row in bundle['jobs']]
        if any(type(value) is not str or not value for value in values) or len(set(values))!=18:
            raise ValueError('campaign_bundle_scope_changed')
    for row in bundle['jobs']:
        model=next(model for model in config['models'] if model['model_id']==row['model_id'])
        source=next(job for job in model['jobs'] if job['cases_root']==row['cases_root'])
        expected_job=_continuation_job(row['model_id'],source,continuation)
        if (row['expected_cases']!=expected_sizes[row['cases_root']]
                or row['max_http_attempts']!=expected_job['max_http_attempts']
                or _amount(row['budget_usd'])!=_amount(expected_job['budget_usd'])):
            raise ValueError('campaign_bundle_scope_changed')
    if continuation is not None and (bundle.get('active_budget_usd')!=format(active_amount,'f')
            or bundle.get('active_max_http_attempts')!=active_attempts or bundle.get('prior_first_case_retry') is not True):
        raise ValueError('continuation_allowance_changed')
    if _recovery_phase(continuation)>=2 and bundle.get('max_output_tokens_all_models')!=2000:
        raise ValueError('continuation_output_limit_changed')
    return bundle,path.parent


def _active_allowance(continuation:dict|None) -> tuple[Decimal,int]:
    if continuation is None:
        return Decimal('10'),192
    debit=continuation.get('inherited_budget_debit_usd',continuation['inherited_unknown_hold_usd'])
    return Decimal('10')-Decimal(debit),192-continuation['inherited_attempts']


def _recovery_phase(continuation:dict|None) -> int:
    return 0 if continuation is None else continuation.get('recovery_phase',1)


def _claim_directory(continuation:dict|None) -> str:
    return {0:'runs/.campaign-claims',1:'runs/.campaign-continuation-claims',
            2:'runs/.campaign-recovery2-claims',3:'runs/.campaign-recovery3-claims',
            4:'runs/.campaign-recovery4-claims'}[_recovery_phase(continuation)]


def _continuation_job(model_id:str,job:dict,continuation:dict|None) -> dict:
    result=deepcopy(job)
    if _recovery_phase(continuation)==4:
        return _continuation_job(model_id,job,continuation['previous_recovery'])
    if _recovery_phase(continuation)==3:
        if model_id=='gpt-6.1-sol':
            return _continuation_job(model_id,job,continuation['previous_recovery'])
        if model_id=='gemini-3.8-flash':
            if job['cases_root']=='cases/question/benchmark-v1':
                result['budget_usd']=format(_amount(job['budget_usd'])-Decimal(continuation['incident_unknown_hold_usd']),'f')
            elif job['cases_root']=='cases/answer/main-v1':
                result['max_http_attempts']=7
        return result
    if continuation is not None and model_id=='gpt-6.1-sol':
        if job['cases_root']=='cases/question/benchmark-v1':
            result['budget_usd']=format(_amount(job['budget_usd'])-Decimal(continuation['inherited_unknown_hold_usd']),'f')
        elif job['cases_root']=='cases/answer/main-v1':
            # Optional B retries move to the already-sent infrastructure attempts.
            # Every one of the sixteen selected inputs remains in each model.
            result['max_http_attempts']=8-continuation['inherited_attempts']
    return result


def _first404_proof(parent_bundle_path:Path,lab:Path) -> dict:
    """Recognize only the one recorded first-request incident, without pricing it zero."""
    path=_inside(parent_bundle_path,lab/'runs')
    raw=read_json(path)
    if raw.get('continuation') is not None:
        raise ValueError('continuation_parent_not_eligible')
    parent,directory=_bundle(path,lab)
    claim=lab/'runs/.campaign-claims/dev-30pct-10usd.json'
    ledger_path=directory/'ledger.json'
    result_path=directory/'campaign-result.json'
    first=parent['jobs'][0]
    first_path=_inside(directory/first['output_path'],directory)
    try:
        claimed=read_json(claim);ledger=read_json(ledger_path);result=read_json(result_path);output=read_json(first_path)
        if (claimed.get('campaign_id')!='dev-30pct-10usd' or claimed.get('campaign_sha256')!=parent['campaign_sha256']
                or claimed.get('bundle_sha256')!=file_sha256(path) or claimed.get('budget_usd_total')!='10.00'
                or claimed.get('max_http_attempts_total')!=192 or ledger.get('campaign_id')!='dev-30pct-10usd'
                or ledger.get('run_state')!='budget_stopped' or ledger.get('current_job_id') is not None
                or result.get('run_state')!='budget_stopped' or result.get('recorded_cases')!=0
                or result.get('succeeded_cases')!=0 or result.get('failed_cases')!=0
                or result.get('unconfirmed_attempts')!=1 or output.get('run_state')!='budget_stopped'
                or output.get('cases')!=[] or output.get('approval_plan_sha256')!=first['plan_sha256']
                or output.get('run_error',{}).get('code')!='response_usage_unconfirmed'
                or first['job_id']!='gpt-6.1-sol-1' or first['model_id']!='gpt-6.1-sol'
                or first['experiment']!='A' or first['cases_root']!='cases/question/benchmark-v1'):
            raise ValueError('continuation_parent_not_eligible')
        prior_plan=read_json(_inside(directory/first['plan_path'],directory))
        if plan_digest(prior_plan)!=first['plan_sha256'] or prior_plan['selected_case_ids'][0]!='a-dev-0001':
            raise ValueError('continuation_parent_not_eligible')
        jobs=ledger.get('jobs')
        if (type(jobs) is not list or len(jobs)!=1 or jobs[0].get('job_id')!=first['job_id']
                or jobs[0].get('recorded_cases')!=0 or jobs[0].get('succeeded_cases')!=0 or jobs[0].get('failed_cases')!=0
                or result.get('jobs')!=jobs or result.get('global_budget')!=ledger.get('global_budget')):
            raise ValueError('continuation_parent_not_eligible')
        budget=ledger['global_budget']
        for key,expected in [('amount_usd','10'),('max_attempts',192),('attempts_started',1),('reserved_usd','0'),
                ('unknown_attempts',1),('in_flight_attempts',0),('halted',True),('halt_reason','actual_cost_unconfirmed'),('debited_upper_usd','0')]:
            if budget.get(key)!=expected:raise ValueError('continuation_parent_not_eligible')
        events=ledger.get('events')
        if type(events) is not list or len(events)!=2:
            raise ValueError('continuation_parent_not_eligible')
        reserved,settled=events
        for event in events:
            if (event.get('attempt_id')!='attempt-1' or event.get('local_attempt_id')!='attempt-1'
                    or event.get('model')!='gpt-6.1-sol' or event.get('job_id')!=first['job_id']
                    or event.get('plan_sha256')!=first['plan_sha256'] or Decimal(event.get('reserved_usd'))!=Decimal('0.09659')):
                raise ValueError('continuation_parent_not_eligible')
        if (reserved.get('event')!='reserved' or settled.get('event')!='settled' or settled.get('http_status')!=404
                or settled.get('sent') is not True or settled.get('cost_status')!='unconfirmed'
                or any(settled.get(key) is not None for key in ('cost_usd','cost_lower_usd','cost_upper_usd','response_id'))
                or any(settled.get(key) is not None for key in ('usage','input_tokens','output_tokens','tokens'))
                or settled.get('error_code')!='response_usage_unconfirmed'):
            raise ValueError('continuation_parent_not_eligible')
    except (KeyError,TypeError,InvalidOperation,OSError):
        raise ValueError('continuation_parent_not_eligible') from None
    return {'version':1,'parent_bundle_path':str(path),'parent_directory':str(directory),'parent_claim_path':str(claim),
        'parent_ledger_path':str(ledger_path),'parent_result_path':str(result_path),'parent_first_result_path':str(first_path),
        'parent_bundle_sha256':file_sha256(path),'parent_claim_sha256':file_sha256(claim),
        'parent_ledger_sha256':file_sha256(ledger_path),'parent_result_sha256':file_sha256(result_path),
        'parent_first_result_sha256':file_sha256(first_path),'inherited_attempts':1,'inherited_unknown_attempts':1,
        'inherited_unknown_hold_usd':format(Decimal(reserved['reserved_usd']),'f'),
        'explicit_user_waiver':'skip provider billing lookup only for the first404; retain its full reserved upper bound',
        'first_case_id':'a-dev-0001','first_job_id':'gpt-6.1-sol-1','prior_cost_status':'unconfirmed',
        'prior_cost_usd':None,'no_unbilled_assumption':True,
        'job_overrides':{'gpt-6.1-sol-1':{'budget_usd':'1.62216','max_http_attempts':22,'lifetime_max_http_attempts':23},
                         'gpt-6.1-sol-2':{'max_http_attempts':7}},'maximum_continuations':1}


def _first400_proof(parent_bundle_path:Path,lab:Path) -> dict:
    """Recognize one additional unpriced request rejected by the proxy's exact cap."""
    path=_inside(parent_bundle_path,lab/'runs')
    raw_parent=read_json(path)
    historical=raw_parent.get('continuation')
    if type(historical) is not dict or _recovery_phase(historical)!=1:
        raise ValueError('continuation_parent_not_eligible')
    parent,directory=_bundle(path,lab) # Also rechecks the untouched original404 chain.
    claim=lab/'runs/.campaign-continuation-claims/dev-30pct-10usd.json'
    ledger_path=directory/'ledger.json';result_path=directory/'campaign-result.json'
    first=parent['jobs'][0]
    first_path=_inside(directory/first['output_path'],directory)
    raw_path=first_path.parent/(first_path.stem+'-raw')/'response-0001.json'
    try:
        claimed=read_json(claim);ledger=read_json(ledger_path);result=read_json(result_path)
        output=read_json(first_path);raw=read_json(raw_path)
        if (claimed.get('campaign_id')!='dev-30pct-10usd' or claimed.get('campaign_sha256')!=parent['campaign_sha256']
                or claimed.get('bundle_sha256')!=file_sha256(path) or claimed.get('budget_usd_total')!='10.00'
                or claimed.get('max_http_attempts_total')!=192 or claimed.get('active_budget_usd')!='9.90341'
                or claimed.get('active_max_http_attempts')!=191 or claimed.get('continuation')!=historical
                or ledger.get('continuation')!=historical or result.get('continuation')!=historical
                or ledger.get('campaign_id')!='dev-30pct-10usd' or ledger.get('run_state')!='budget_stopped'
                or ledger.get('current_job_id') is not None or result.get('run_state')!='budget_stopped'
                or any(result.get(key)!=0 for key in ('recorded_cases','succeeded_cases','failed_cases'))
                or result.get('unconfirmed_attempts')!=2 or result.get('settled_attempts')!=2
                or result.get('active_settled_attempts')!=1 or output.get('run_state')!='budget_stopped'
                or output.get('cases')!=[] or output.get('approval_plan_sha256')!=first['plan_sha256']
                or output.get('run_error',{}).get('code')!='response_usage_unconfirmed'
                or first['job_id']!='gpt-6.1-sol-1' or first['model_id']!='gpt-6.1-sol'
                or first['experiment']!='A' or first['cases_root']!='cases/question/benchmark-v1'
                or any(_inside(directory/row['output_path'],directory).exists() for row in parent['jobs'][1:])):
            raise ValueError('continuation_parent_not_eligible')
        prior_plan=read_json(_inside(directory/first['plan_path'],directory))
        if (plan_digest(prior_plan)!=first['plan_sha256'] or prior_plan['selected_case_ids'][0]!='a-dev-0001'
                or prior_plan['limits']['max_output_tokens']!=4096 or prior_plan['limits']['stream'] is not False):
            raise ValueError('continuation_parent_not_eligible')
        jobs=ledger.get('jobs')
        if (type(jobs) is not list or len(jobs)!=1 or jobs[0].get('job_id')!=first['job_id']
                or any(jobs[0].get(key)!=0 for key in ('recorded_cases','succeeded_cases','failed_cases'))
                or result.get('jobs')!=jobs or result.get('global_budget')!=ledger.get('global_budget')):
            raise ValueError('continuation_parent_not_eligible')
        budget=ledger['global_budget']
        expected_budget={'amount_usd':'10','max_attempts':192,'attempts_started':2,'reserved_usd':'0',
            'unknown_attempts':2,'in_flight_attempts':0,'halted':True,'halt_reason':'actual_cost_unconfirmed',
            'debited_upper_usd':'0.09659','active_amount_usd':'9.90341','active_max_attempts':191,
            'active_attempts_started':1,'new_unknown_attempts':1,'new_debited_upper_usd':'0',
            'inherited_unknown_hold_usd':'0.09659','inherited_unknown_attempts':1}
        if any(budget.get(key)!=expected for key,expected in expected_budget.items()):
            raise ValueError('continuation_parent_not_eligible')
        events=ledger.get('events')
        if type(events) is not list or len(events)!=2:
            raise ValueError('continuation_parent_not_eligible')
        reserved,settled=events
        for event in events:
            if (event.get('attempt_id')!='attempt-1' or event.get('local_attempt_id')!='attempt-1'
                    or event.get('lifetime_attempt_id')!='attempt-2' or event.get('model')!='gpt-6.1-sol'
                    or event.get('job_id')!=first['job_id'] or event.get('plan_sha256')!=first['plan_sha256']
                    or Decimal(event.get('reserved_usd'))!=Decimal('0.09659')):
                raise ValueError('continuation_parent_not_eligible')
        if (reserved.get('event')!='reserved' or settled.get('event')!='settled' or settled.get('http_status')!=400
                or settled.get('sent') is not True or settled.get('cost_status')!='unconfirmed'
                or any(settled.get(key) is not None for key in ('cost_usd','cost_lower_usd','cost_upper_usd',
                    'response_id','usage','input_tokens','output_tokens','tokens'))
                or settled.get('error_code')!='response_usage_unconfirmed'):
            raise ValueError('continuation_parent_not_eligible')
        if raw.get('error')!={'message':NONSTREAM_CAP_MESSAGE,'type':'invalid_request_error','param':None,'code':'400'}:
            raise ValueError('continuation_parent_not_eligible')
        diagnostic=raw.get('_elice_diagnostic',{})
        expected_diagnostic={'kind':'http_error','http_status':400,'model':'gpt-6.1-sol','attempt_id':'attempt-1',
            'captured_body_bytes':418,'body_sha256':'45ed0abe894f198cc35984c66f3ae3fa274e38dba16fb98b811c81db3e5f45df',
            'hash_scope':'captured_body_bytes','body_truncated':False,'body_kind':'json','error_code':'response_usage_unconfirmed'}
        if any(diagnostic.get(key)!=expected for key,expected in expected_diagnostic.items()):
            raise ValueError('continuation_parent_not_eligible')
        billing=raw.get('_elice_billing',{})
        if (any(billing.get(key) is not None for key in ('usage','cost_usd','cost_lower_usd','cost_upper_usd','provider_model'))
                or billing.get('cost_status')!='unconfirmed' or billing.get('canonical_model')!='gpt-6.1-sol'
                or billing.get('attempt_id')!='attempt-1' or billing.get('accounting_basis')!='billing_upper_bound'):
            raise ValueError('continuation_parent_not_eligible')
    except (KeyError,TypeError,InvalidOperation,OSError):
        raise ValueError('continuation_parent_not_eligible') from None
    hold=Decimal(historical['inherited_unknown_hold_usd'])+Decimal(reserved['reserved_usd'])
    return {'version':1,'recovery_phase':2,'maximum_recovery_phase':2,
        'parent_bundle_path':str(path),'parent_directory':str(directory),
        'parent_directories':[historical['parent_directory'],str(directory)],
        'parent_claim_path':str(claim),'parent_ledger_path':str(ledger_path),'parent_result_path':str(result_path),
        'parent_first_result_path':str(first_path),'parent_raw_path':str(raw_path),
        'parent_bundle_sha256':file_sha256(path),'parent_claim_sha256':file_sha256(claim),
        'parent_ledger_sha256':file_sha256(ledger_path),'parent_result_sha256':file_sha256(result_path),
        'parent_first_result_sha256':file_sha256(first_path),'parent_raw_sha256':file_sha256(raw_path),
        'original_first404':deepcopy(historical),'inherited_attempts':2,'inherited_unknown_attempts':2,
        'inherited_unknown_hold_usd':format(hold,'f'),'first_case_id':'a-dev-0001','first_job_id':'gpt-6.1-sol-1',
        'explicit_user_waiver':'continue within the original USD10/192 scope without provider billing lookup; '
            'hold both unknown reservations and apply the observed non-streaming2000 ceiling to all models',
        'prior_cost_status':'unconfirmed','prior_cost_usd':None,'no_unbilled_assumption':True,
        'max_output_tokens_all_models':2000,
        'job_overrides':{'gpt-6.1-sol-1':{'budget_usd':'1.52557','max_http_attempts':22,'lifetime_max_http_attempts':24},
                         'gpt-6.1-sol-2':{'max_http_attempts':6}}}


def _unsupported_text_proof(parent_bundle_path:Path,lab:Path) -> dict:
    """Reuse only this completed prefix after the exact third infrastructure incident."""
    path=_inside(parent_bundle_path,lab/'runs')
    raw_parent=read_json(path)
    historical=raw_parent.get('continuation')
    if type(historical) is not dict or _recovery_phase(historical)!=2:
        raise ValueError('continuation_parent_not_eligible')
    parent,directory=_bundle(path,lab)
    claim=lab/'runs/.campaign-recovery2-claims/dev-30pct-10usd.json'
    ledger_path=directory/'ledger.json';result_path=directory/'campaign-result.json'
    incident=parent['jobs'][3]
    incident_path=_inside(directory/incident['output_path'],directory)
    raw_path=incident_path.parent/(incident_path.stem+'-raw')/'response-0001.json'
    try:
        claimed=read_json(claim);ledger=read_json(ledger_path);result=read_json(result_path)
        output=read_json(incident_path);raw=read_json(raw_path)
        if (claimed.get('campaign_id')!='dev-30pct-10usd' or claimed.get('campaign_sha256')!=parent['campaign_sha256']
                or claimed.get('bundle_sha256')!=file_sha256(path) or claimed.get('budget_usd_total')!='10.00'
                or claimed.get('max_http_attempts_total')!=192 or claimed.get('active_budget_usd')!='9.80682'
                or claimed.get('active_max_http_attempts')!=190 or claimed.get('continuation')!=historical
                or ledger.get('continuation')!=historical or result.get('continuation')!=historical
                or ledger.get('campaign_id')!='dev-30pct-10usd' or ledger.get('run_state')!='budget_stopped'
                or ledger.get('current_job_id') is not None or result.get('run_state')!='budget_stopped'
                or result.get('recorded_cases')!=16 or result.get('succeeded_cases')!=16 or result.get('failed_cases')!=0
                or result.get('unconfirmed_attempts')!=3 or result.get('settled_attempts')!=30
                or result.get('active_settled_attempts')!=28 or result.get('bounded_cost_attempts')!=14
                or result.get('confirmed_cost_known_subtotal_usd')!='0.3430030'
                or output.get('run_state')!='budget_stopped' or output.get('cases')!=[]
                or output.get('approval_plan_sha256')!=incident['plan_sha256']
                or output.get('run_error',{}).get('code')!='response_usage_unconfirmed'
                or incident['job_id']!='gemini-3.8-flash-1' or incident['model_id']!='gemini-3.8-flash'
                or incident['experiment']!='A' or incident['cases_root']!='cases/question/benchmark-v1'
                or any(_inside(directory/row['output_path'],directory).exists() for row in parent['jobs'][4:])):
            raise ValueError('continuation_parent_not_eligible')
        jobs=ledger.get('jobs')
        if (type(jobs) is not list or len(jobs)!=4 or result.get('jobs')!=jobs
                or result.get('global_budget')!=ledger.get('global_budget')
                or [job.get('job_id') for job in jobs]!=PREFIX_JOB_IDS+['gemini-3.8-flash-1']
                or any(jobs[3].get(key)!=0 for key in ('recorded_cases','succeeded_cases','failed_cases'))):
            raise ValueError('continuation_parent_not_eligible')
        reused=[]
        plans={}
        for row in parent['jobs'][:4]:
            plan_path=_inside(directory/row['plan_path'],directory)
            plan=read_json(plan_path)
            if (plan_digest(plan)!=row['plan_sha256'] or plan['model_ids']!=[row['model_id']]
                    or plan['limits']['max_output_tokens']!=2000 or plan['limits']['stream'] is not False):
                raise ValueError('continuation_parent_not_eligible')
            plans[row['job_id']]=plan
        if plans[incident['job_id']]['selected_case_ids'][0]!='a-dev-0001':
            raise ValueError('continuation_parent_not_eligible')
        for row,summary in zip(parent['jobs'][:3],jobs[:3],strict=True):
            output_path=_inside(directory/row['output_path'],directory)
            value=read_json(output_path);plan=plans[row['job_id']]
            records=value.get('cases')
            if (row['job_id'] not in PREFIX_JOB_IDS or row['model_id']!='gpt-6.1-sol'
                    or summary.get('run_state')!='completed' or summary.get('recorded_cases')!=row['expected_cases']
                    or summary.get('succeeded_cases')!=row['expected_cases'] or summary.get('failed_cases')!=0
                    or value.get('run_state')!='completed' or value.get('approval_plan_sha256')!=row['plan_sha256']
                    or type(records) is not list or len(records)!=row['expected_cases']
                    or any(record.get('status')!='succeeded' for record in records)):
                raise ValueError('continuation_parent_not_eligible')
            ids=[]
            for record in records:
                identity=record.get('case_id') if row['experiment']=='B' else record.get('case')
                if type(identity) is not str:
                    raise ValueError('continuation_parent_not_eligible')
                if row['experiment']=='A':
                    identity,separator,version=identity.rpartition('.v')
                    if separator!='.v' or not version.isdigit():
                        raise ValueError('continuation_parent_not_eligible')
                ids.append(identity)
            if ids!=plan['selected_case_ids'] or len(set(ids))!=len(ids):
                raise ValueError('continuation_parent_not_eligible')
            plan_path=_inside(directory/row['plan_path'],directory)
            reused.append({'job_id':row['job_id'],'model_id':row['model_id'],'experiment':row['experiment'],
                'cases_root':row['cases_root'],'expected_cases':row['expected_cases'],
                'output_path':str(output_path),'output_sha256':file_sha256(output_path),
                'plan_path':str(plan_path),'plan_sha256':row['plan_sha256'],'plan_file_sha256':file_sha256(plan_path),
                'selected_case_ids':ids,'source_directory':str(directory)})
        budget=ledger['global_budget']
        expected_budget={'amount_usd':'10','max_attempts':192,'attempts_started':30,'reserved_usd':'0',
            'unknown_attempts':3,'in_flight_attempts':0,'halted':True,'halt_reason':'actual_cost_unconfirmed',
            'debited_upper_usd':'0.7236722','active_amount_usd':'9.80682','active_max_attempts':190,
            'active_attempts_started':28,'new_unknown_attempts':1,'new_debited_upper_usd':'0.5304922',
            'inherited_unknown_hold_usd':'0.19318','inherited_unknown_attempts':2}
        if any(budget.get(key)!=expected for key,expected in expected_budget.items()):
            raise ValueError('continuation_parent_not_eligible')
        events=ledger.get('events')
        if type(events) is not list or len(events)!=56:
            raise ValueError('continuation_parent_not_eligible')
        known_upper=Decimal(0);exact=Decimal(0);bounded=0
        for index in range(1,29):
            reserved,settled=events[2*index-2:2*index]
            job_id=('gpt-6.1-sol-1' if index<=22 else 'gpt-6.1-sol-2' if index<=26
                else 'gpt-6.1-sol-3' if index==27 else 'gemini-3.8-flash-1')
            local=index if index<=22 else index-22 if index<=26 else 1
            model='gpt-6.1-sol' if index<=27 else 'gemini-3.8-flash'
            for event,kind in ((reserved,'reserved'),(settled,'settled')):
                if (event.get('event')!=kind or event.get('attempt_id')!=f'attempt-{index}'
                        or event.get('local_attempt_id')!=f'attempt-{local}'
                        or event.get('lifetime_attempt_id')!=f'attempt-{index+2}'
                        or event.get('job_id')!=job_id or event.get('model')!=model
                        or event.get('plan_sha256')!=next(row['plan_sha256'] for row in parent['jobs'] if row['job_id']==job_id)
                        or _amount(event.get('reserved_usd'))!=_amount(reserved.get('reserved_usd'))):
                    raise ValueError('continuation_parent_not_eligible')
            if settled.get('sent') is not True or settled.get('http_status')!=(200 if index<=27 else 400):
                raise ValueError('continuation_parent_not_eligible')
            if index<=27:
                upper=_amount(settled.get('cost_upper_usd'));lower=Decimal(settled['cost_lower_usd'])
                if not lower.is_finite() or not Decimal(0)<=lower<=upper<=_amount(reserved['reserved_usd']):
                    raise ValueError('continuation_parent_not_eligible')
                known_upper+=upper
                if settled.get('cost_status')=='confirmed':
                    cost=_amount(settled.get('cost_usd'))
                    if cost!=upper or cost!=lower:raise ValueError('continuation_parent_not_eligible')
                    exact+=cost
                elif settled.get('cost_status')=='bounded' and settled.get('cost_usd') is None:
                    bounded+=1
                else:raise ValueError('continuation_parent_not_eligible')
            elif (_amount(reserved['reserved_usd'])!=Decimal('0.02419275')
                    or settled.get('cost_status')!='unconfirmed'
                    or any(settled.get(key) is not None for key in ('cost_usd','cost_lower_usd','cost_upper_usd',
                        'response_id','usage','input_tokens','output_tokens','tokens'))
                    or settled.get('error_code')!='response_usage_unconfirmed'):
                raise ValueError('continuation_parent_not_eligible')
        if known_upper!=Decimal('0.5304922') or exact!=Decimal('0.3430030') or bounded!=14:
            raise ValueError('continuation_parent_not_eligible')
        if raw.get('error')!={'message':UNSUPPORTED_TEXT_MESSAGE,'type':'invalid_request_error','param':None,'code':'400'}:
            raise ValueError('continuation_parent_not_eligible')
        diagnostic=raw.get('_elice_diagnostic',{})
        expected_diagnostic={'kind':'http_error','http_status':400,'model':'gemini-3.8-flash','attempt_id':'attempt-28',
            'captured_body_bytes':244,'body_sha256':'163efdfcb9029ebaf23b060bfd60d928d61f7bdc79a6db71a9cb698d801a7579',
            'hash_scope':'captured_body_bytes','body_truncated':False,'body_kind':'json','error_code':'response_usage_unconfirmed'}
        if any(diagnostic.get(key)!=expected for key,expected in expected_diagnostic.items()):
            raise ValueError('continuation_parent_not_eligible')
        billing=raw.get('_elice_billing',{})
        if (any(billing.get(key) is not None for key in ('usage','cost_usd','cost_lower_usd','cost_upper_usd','provider_model'))
                or billing.get('cost_status')!='unconfirmed' or billing.get('canonical_model')!='gemini-3.8-flash'
                or billing.get('attempt_id')!='attempt-28' or billing.get('accounting_basis')!='billing_upper_bound'):
            raise ValueError('continuation_parent_not_eligible')
    except (KeyError,TypeError,InvalidOperation,OSError,PolicyError):
        raise ValueError('continuation_parent_not_eligible') from None
    incident_hold=Decimal('0.02419275')
    hold=Decimal(historical['inherited_unknown_hold_usd'])+incident_hold
    return {'version':1,'recovery_phase':3,'maximum_recovery_phase':3,'previous_recovery':deepcopy(historical),
        'parent_bundle_path':str(path),'parent_directory':str(directory),
        'parent_directories':historical['parent_directories']+[str(directory)],
        'parent_claim_path':str(claim),'parent_ledger_path':str(ledger_path),'parent_result_path':str(result_path),
        'parent_incident_result_path':str(incident_path),'parent_raw_path':str(raw_path),
        'parent_bundle_sha256':file_sha256(path),'parent_claim_sha256':file_sha256(claim),
        'parent_ledger_sha256':file_sha256(ledger_path),'parent_result_sha256':file_sha256(result_path),
        'parent_incident_result_sha256':file_sha256(incident_path),'parent_raw_sha256':file_sha256(raw_path),
        'reused_completed_outputs':reused,'reused_completed_job_ids':deepcopy(PREFIX_JOB_IDS),
        'execution_job_ids':deepcopy(REMAINING_JOB_IDS),'execution_order_reason':'Run Luna before Sonnet to preserve progress if strict schema is unsupported.',
        'inherited_attempts':30,'inherited_unknown_attempts':3,'inherited_known_debited_upper_usd':format(known_upper,'f'),
        'inherited_unknown_hold_usd':format(hold,'f'),'incident_unknown_hold_usd':format(incident_hold,'f'),
        'inherited_budget_debit_usd':format(known_upper+hold,'f'),
        'inherited_confirmed_cost_known_subtotal_usd':format(exact,'f'),'inherited_bounded_cost_attempts':bounded,
        'incident_job_id':'gemini-3.8-flash-1','incident_case_id':'a-dev-0001','incident_lifetime_attempt_id':'attempt-30',
        'wire_protocol_by_model':deepcopy(WIRE_PROTOCOL_BY_MODEL),'max_output_tokens_all_models':2000,
        'strict_schema_required':True,'no_unbilled_assumption':True,'prior_cost_status':'three unknown attempts retained as holds',
        'explicit_user_waiver':'Continue the original USD10/192 campaign without billing lookup, reuse all completed Sol cases, '
            'retain known upper debits and every unknown hold; preserve strict schema over the provider-supported wire protocol.'}


def _cancelled_terminal_proof(parent_bundle_path:Path,lab:Path) -> dict:
    """Skip only the final unrecorded Argon A case, preserving its cancelled attempt."""
    path=_inside(parent_bundle_path,lab/'runs');raw_parent=read_json(path)
    historical=raw_parent.get('continuation')
    if type(historical) is not dict or _recovery_phase(historical)!=3:
        raise ValueError('continuation_parent_not_eligible')
    parent,directory=_bundle(path,lab)
    claim=lab/'runs/.campaign-recovery3-claims/dev-30pct-10usd.json'
    ledger_path=directory/'ledger.json';result_path=directory/'campaign-result.json'
    incident=next(row for row in parent['jobs'] if row['job_id']=='gemini-4-argon-1')
    incident_path=_inside(directory/incident['output_path'],directory)
    try:
        claimed=read_json(claim);ledger=read_json(ledger_path);result=read_json(result_path)
        if (claimed.get('campaign_id')!='dev-30pct-10usd' or claimed.get('campaign_sha256')!=parent['campaign_sha256']
                or claimed.get('bundle_sha256')!=file_sha256(path) or claimed.get('budget_usd_total')!='10.00'
                or claimed.get('max_http_attempts_total')!=192 or claimed.get('active_budget_usd')!='9.25213505'
                or claimed.get('active_max_http_attempts')!=162 or claimed.get('continuation')!=historical
                or ledger.get('continuation')!=historical or result.get('continuation')!=historical
                or ledger.get('campaign_id')!='dev-30pct-10usd' or ledger.get('run_state')!='budget_stopped'
                or ledger.get('current_job_id') is not None or result.get('run_state')!='budget_stopped'
                or result.get('recorded_cases')!=42 or result.get('succeeded_cases')!=34 or result.get('failed_cases')!=8
                or result.get('unconfirmed_attempts')!=4 or result.get('settled_attempts')!=70
                or result.get('active_settled_attempts')!=40 or result.get('bounded_cost_attempts')!=17
                or result.get('confirmed_cost_known_subtotal_usd')!='0.84390675'
                or result.get('jobs')!=ledger.get('jobs') or result.get('global_budget')!=ledger.get('global_budget')):
            raise ValueError('continuation_parent_not_eligible')
        jobs=ledger['jobs']
        if [row.get('job_id') for row in jobs]!=TERMINAL_PREFIX_JOB_IDS:
            raise ValueError('continuation_parent_not_eligible')
        by_id={row['job_id']:row for row in parent['jobs']}
        if any(_inside(directory/by_id[identifier]['output_path'],directory).exists() for identifier in TERMINAL_REMAINING_JOB_IDS):
            raise ValueError('continuation_parent_not_eligible')
        reused=deepcopy(historical['reused_completed_outputs'])
        for entry,summary in zip(reused,jobs[:3],strict=True):
            count=entry['expected_cases']
            if (summary.get('reused') is not True or summary.get('source_output_path')!=entry['output_path']
                    or summary.get('source_output_sha256')!=entry['output_sha256'] or summary.get('recorded_cases')!=count
                    or summary.get('succeeded_cases')!=count or summary.get('failed_cases')!=0):
                raise ValueError('continuation_parent_not_eligible')
            entry.update(original_recorded_cases=count,recorded_case_ids=entry['selected_case_ids'],
                logical_terminal_cases=count,terminal_failure_observations=0,succeeded_cases=count,failed_cases=0,
                source_failed_cases=0,partial_terminal=False,source_run_state='completed')
        plans={}
        for summary in jobs[3:]:
            job=by_id[summary['job_id']];partial=job['job_id']=='gemini-4-argon-1'
            plan_path=_inside(directory/job['plan_path'],directory);plan=read_json(plan_path)
            output_path=_inside(directory/job['output_path'],directory);value=read_json(output_path)
            plans[job['job_id']]=plan
            records=value.get('cases');expected=10 if partial else job['expected_cases']
            successes=10 if partial else 3 if job['job_id']=='gemini-3.8-flash-1' else expected
            failures=8 if job['job_id']=='gemini-3.8-flash-1' else 0
            state='budget_stopped' if partial else 'completed'
            if (plan_digest(plan)!=job['plan_sha256'] or plan['model_ids']!=[job['model_id']]
                    or plan['limits']['max_output_tokens']!=2000 or plan['limits']['stream'] is not False
                    or value.get('approval_plan_sha256')!=job['plan_sha256'] or value.get('run_state')!=state
                    or summary.get('run_state')!=state or summary.get('recorded_cases')!=expected
                    or summary.get('succeeded_cases')!=successes or summary.get('failed_cases')!=failures
                    or type(records) is not list or len(records)!=expected
                    or sum(record.get('status')=='succeeded' for record in records)!=successes
                    or sum(record.get('status') in {'failed','rejected'} for record in records)!=failures):
                raise ValueError('continuation_parent_not_eligible')
            ids=[]
            for record in records:
                identity=record.get('case_id') if job['experiment']=='B' else record.get('case')
                if type(identity) is not str:raise ValueError('continuation_parent_not_eligible')
                if job['experiment']=='A':
                    identity,separator,version=identity.rpartition('.v')
                    if separator!='.v' or not version.isdigit():raise ValueError('continuation_parent_not_eligible')
                ids.append(identity)
            if ids!=plan['selected_case_ids'][:expected] or len(set(ids))!=expected:
                raise ValueError('continuation_parent_not_eligible')
            if partial and (plan['selected_case_ids'][-1]!='a-dev-0025'
                    or value.get('checkpoint')!={'completed':10,'total':11,'current_case':'a-dev-0025.v1'}
                    or value.get('run_error',{}).get('code')!='attempt_cancelled'):
                raise ValueError('continuation_parent_not_eligible')
            reused.append({'job_id':job['job_id'],'model_id':job['model_id'],'experiment':job['experiment'],
                'cases_root':job['cases_root'],'expected_cases':job['expected_cases'],'output_path':str(output_path),
                'output_sha256':file_sha256(output_path),'plan_path':str(plan_path),'plan_sha256':job['plan_sha256'],
                'plan_file_sha256':file_sha256(plan_path),'selected_case_ids':plan['selected_case_ids'],
                'recorded_case_ids':ids,'original_recorded_cases':expected,'logical_terminal_cases':job['expected_cases'],
                'terminal_failure_observations':int(partial),'partial_terminal':partial,'succeeded_cases':successes,
                'failed_cases':failures+int(partial),'source_failed_cases':failures,'source_run_state':state,
                'source_directory':str(directory)})
        expected_budget={'amount_usd':'10','max_attempts':192,'attempts_started':70,'reserved_usd':'0',
            'unknown_attempts':4,'in_flight_attempts':0,'halted':True,'halt_reason':'actual_cost_unconfirmed',
            'debited_upper_usd':'1.29728120','active_amount_usd':'9.25213505','active_max_attempts':162,
            'active_attempts_started':40,'new_unknown_attempts':1,'new_debited_upper_usd':'0.54941625',
            'inherited_unknown_hold_usd':'0.21737275','inherited_unknown_attempts':3,
            'inherited_known_debited_upper_usd':'0.5304922','inherited_budget_debit_usd':'0.74786495'}
        if any(ledger['global_budget'].get(key)!=expected for key,expected in expected_budget.items()):
            raise ValueError('continuation_parent_not_eligible')
        events=ledger.get('events');known=Decimal(0);exact=Decimal(0);bounded=0
        if type(events) is not list or len(events)!=80:raise ValueError('continuation_parent_not_eligible')
        for index in range(1,41):
            reserved,settled=events[2*index-2:2*index]
            job_id=('gemini-3.8-flash-1' if index<=14 else 'gemini-3.8-flash-2' if index<=18
                else 'gemini-3.8-flash-3' if index==19 else 'gemini-4-argon-1')
            local=index if index<=14 else index-14 if index<=18 else 1 if index==19 else index-19
            for event,kind in ((reserved,'reserved'),(settled,'settled')):
                if (event.get('event')!=kind or event.get('attempt_id')!=f'attempt-{index}'
                        or event.get('local_attempt_id')!=f'attempt-{local}' or event.get('lifetime_attempt_id')!=f'attempt-{index+30}'
                        or event.get('job_id')!=job_id or event.get('model')!=by_id[job_id]['model_id']
                        or event.get('plan_sha256')!=by_id[job_id]['plan_sha256'] or event.get('wire_protocol')!='chat_completions'
                        or _amount(event.get('reserved_usd'))!=_amount(reserved.get('reserved_usd'))):
                    raise ValueError('continuation_parent_not_eligible')
            if settled.get('sent') is not True:raise ValueError('continuation_parent_not_eligible')
            if index<=39:
                upper=_amount(settled.get('cost_upper_usd'));lower=Decimal(settled['cost_lower_usd'])
                if (settled.get('http_status')!=200 or not lower.is_finite()
                        or not Decimal(0)<=lower<=upper<=_amount(reserved['reserved_usd'])):
                    raise ValueError('continuation_parent_not_eligible')
                known+=upper
                if settled.get('cost_status')=='confirmed':
                    cost=_amount(settled.get('cost_usd'))
                    if cost!=upper or cost!=lower:raise ValueError('continuation_parent_not_eligible')
                    exact+=cost
                elif settled.get('cost_status')=='bounded' and settled.get('cost_usd') is None:bounded+=1
                else:raise ValueError('continuation_parent_not_eligible')
            elif (settled.get('http_status') is not None or settled.get('error_code')!='attempt_cancelled'
                    or settled.get('cost_status')!='unconfirmed' or _amount(reserved['reserved_usd'])!=Decimal('.080842')
                    or any(settled.get(key) is not None for key in ('cost_usd','cost_lower_usd','cost_upper_usd',
                        'response_id','usage','input_tokens','output_tokens','tokens'))):
                raise ValueError('continuation_parent_not_eligible')
        if known!=Decimal('.54941625') or exact!=Decimal('.50090375') or bounded!=3:
            raise ValueError('continuation_parent_not_eligible')
    except (KeyError,TypeError,InvalidOperation,OSError,PolicyError):
        raise ValueError('continuation_parent_not_eligible') from None
    known_total=Decimal(historical['inherited_known_debited_upper_usd'])+known
    hold=Decimal(historical['inherited_unknown_hold_usd'])+Decimal('.080842')
    observation={'job_id':'gemini-4-argon-1','model_id':'gemini-4-argon','case_id':'a-dev-0025','case':'a-dev-0025.v1',
        'status':'interrupted','source_attempt_id':'attempt-40','source_lifetime_attempt_id':'attempt-70',
        'source_local_attempt_id':'attempt-21','source_directory':str(directory),'source_result_path':str(incident_path),
        'source_result_sha256':file_sha256(incident_path),'source_ledger_path':str(ledger_path),
        'source_ledger_sha256':file_sha256(ledger_path),'error_code':'attempt_cancelled','http_status':None,
        'input_tokens':None,'output_tokens':None,'actual_cost_usd':None,'output':None,'raw_response_path':None,
        'reserved_upper_usd':'0.080842','retry_planned':False}
    return {'version':1,'recovery_phase':4,'maximum_recovery_phase':4,'previous_recovery':deepcopy(historical),
        'parent_bundle_path':str(path),'parent_directory':str(directory),
        'parent_directories':historical['parent_directories']+[str(directory)],
        'parent_claim_path':str(claim),'parent_ledger_path':str(ledger_path),'parent_result_path':str(result_path),
        'parent_incident_result_path':str(incident_path),'parent_bundle_sha256':file_sha256(path),
        'parent_claim_sha256':file_sha256(claim),'parent_ledger_sha256':file_sha256(ledger_path),
        'parent_result_sha256':file_sha256(result_path),'parent_incident_result_sha256':file_sha256(incident_path),
        'reused_completed_outputs':reused,'reused_completed_job_ids':deepcopy(TERMINAL_PREFIX_JOB_IDS),
        'execution_job_ids':deepcopy(TERMINAL_REMAINING_JOB_IDS),'terminal_case_observations':[observation],
        'inherited_attempts':70,'inherited_unknown_attempts':4,'inherited_known_debited_upper_usd':format(known_total,'f'),
        'inherited_unknown_hold_usd':format(hold,'f'),'inherited_budget_debit_usd':format(known_total+hold,'f'),
        'inherited_confirmed_cost_known_subtotal_usd':format(Decimal(historical['inherited_confirmed_cost_known_subtotal_usd'])+exact,'f'),
        'inherited_bounded_cost_attempts':historical['inherited_bounded_cost_attempts']+bounded,
        'wire_protocol_by_model':deepcopy(historical['wire_protocol_by_model']),'max_output_tokens_all_models':2000,
        'strict_schema_required':True,'no_unbilled_assumption':True,
        'explicit_user_waiver':'Skip the cancelled final Argon A case without retry; preserve all terminal outputs and unknown holds '
            'and run only the remaining jobs within the original USD10/192 scope.'}


def _verify_continuation(proof:dict,lab:Path) -> None:
    try:
        if type(proof) is not dict:
            raise ValueError('continuation_parent_changed')
        phase=_recovery_phase(proof)
        factory={1:_first404_proof,2:_first400_proof,3:_unsupported_text_proof,4:_cancelled_terminal_proof}.get(phase)
        if factory is None or proof!=factory(Path(proof['parent_bundle_path']),lab):
            raise ValueError('continuation_parent_changed')
    except (ValueError,KeyError,TypeError,OSError):
        raise ValueError('continuation_parent_changed') from None


def prepare_continuation(parent_bundle_path:Path,output_dir:Path,*,env_path:Path|None=None,
                         lab_root:Path|None=None) -> dict:
    """Prepare only an exact recorded recovery, preserving completed work and all debits."""
    lab=Path(lab_root or LAB_ROOT).resolve()
    path=_inside(parent_bundle_path,lab/'runs')
    parent=read_json(path)
    factory={0:_first404_proof,1:_first400_proof,2:_unsupported_text_proof,3:_cancelled_terminal_proof}.get(_recovery_phase(parent.get('continuation')))
    if factory is None:raise ValueError('continuation_parent_not_eligible')
    proof=factory(path,lab)
    if (lab/_claim_directory(proof)/'dev-30pct-10usd.json').exists():
        raise ValueError('continuation_already_claimed')
    return prepare_campaign(Path(parent['devon_root']),Path(parent['campaign_path']),output_dir,
        env_path=env_path,lab_root=lab,_continuation=proof)


def _policy_for(job:dict,bundle:dict,directory:Path,env:Path,lab:Path):
    from run_lab import _credentials
    plan_path=_inside(directory/job['plan_path'],directory)
    approval_path=_inside(directory/job['approval_path'],directory)
    output_path=_inside(directory/job['output_path'],directory)
    plan=read_json(plan_path)
    if plan_digest(plan)!=job['plan_sha256'] or plan['model_ids']!=[job['model_id']]:
        raise ValueError('campaign_plan_changed')
    if (_amount(job['budget_usd'])!=_amount(plan['budget_usd'])
            or job['max_http_attempts']!=plan['max_http_attempts']
            or job['expected_cases']!=len(plan['selected_case_ids'])
            or plan['config'].get('campaign_path')!=bundle['campaign_path']
            or plan['config'].get('selection_path')!=bundle['selection_path']):
        raise ValueError('campaign_job_changed')
    _,endpoint=_credentials(env,lab,model_id=job['model_id'])
    config=plan['config']
    policy=validate_execution(plan,devon_root=bundle['devon_root'],cases_path=config['cases_path'],
        manifest_path=config['manifest_path'],pricing_path=config['pricing_path'],approval_path=approval_path,
        base_url=endpoint,output_root=output_path.parent)
    return policy,plan_path,approval_path,output_path


class _Ledger:
    def __init__(self,path:Path,budget:CostBudget,bundle:dict):
        self.path,self.budget,self.bundle=path,budget,bundle
        self.events=[]
        self.jobs=[]
        self.current_job_id=None
        self.state='running'
        self.lock=threading.Lock()

    def snapshot(self):
        state=self.budget.to_dict()
        active_debit=Decimal(state.pop('spent_usd'))
        continuation=self.bundle.get('continuation')
        if continuation is None:
            state['debited_upper_usd']=format(active_debit,'f')
        else:
            hold=Decimal(continuation['inherited_unknown_hold_usd'])
            inherited_debit=Decimal(continuation.get('inherited_budget_debit_usd',continuation['inherited_unknown_hold_usd']))
            state['active_amount_usd']=state['amount_usd']
            state['active_max_attempts']=state['max_attempts']
            state['active_attempts_started']=state['attempts_started']
            state['new_unknown_attempts']=state['unknown_attempts']
            state['new_debited_upper_usd']=format(active_debit,'f')
            state['amount_usd']='10'
            state['max_attempts']=192
            state['attempts_started']+=continuation['inherited_attempts']
            state['unknown_attempts']+=continuation['inherited_unknown_attempts']
            state['inherited_unknown_hold_usd']=format(hold,'f')
            state['inherited_unknown_attempts']=continuation['inherited_unknown_attempts']
            state['debited_upper_usd']=format(active_debit+inherited_debit,'f')
            if _recovery_phase(continuation)>=3:
                state['inherited_known_debited_upper_usd']=continuation['inherited_known_debited_upper_usd']
                state['inherited_budget_debit_usd']=continuation['inherited_budget_debit_usd']
            state['prior_cost_status']='unconfirmed; held at original reservation upper bound'
        state['accounting_basis']='conservative billing upper-bound debits, not confirmed invoice cost'
        state['transport_integration']='elice_global_guard'
        return state

    def save(self):
        _atomic(self.path,{'version':1,'campaign_id':self.bundle['campaign_id'],'run_state':self.state,
            'global_budget':self.snapshot(),'current_job_id':self.current_job_id,'jobs':self.jobs,'events':self.events,
            'continuation':self.bundle.get('continuation')})

    def audit(self,event:dict):
        with self.lock:
            row=deepcopy(event)
            row['job_id']=self.current_job_id
            continuation=self.bundle.get('continuation')
            if continuation is not None:
                attempt=row.get('attempt_id')
                if type(attempt) is str and attempt.startswith('attempt-') and attempt[8:].isdigit():
                    row['active_attempt_id']=attempt
                    row['lifetime_attempt_id']='attempt-'+str(int(attempt[8:])+continuation['inherited_attempts'])
                row['lifetime_global_budget']=self.snapshot()
            self.events.append(row)
            self.save() # synchronous durable write; failure propagates before HTTP.


async def execute_campaign(bundle_path:Path,*,env_path:Path|None=None,lab_root:Path|None=None,
                           execute_plan=None) -> dict:
    """Run the fixed campaign or one of its exact pinned recoveries; no automatic resume."""
    lab=Path(lab_root or LAB_ROOT).resolve()
    bundle,directory=_bundle(Path(bundle_path),lab)
    campaign=Path(bundle['campaign_path'])
    continuation=bundle.get('continuation')
    claim_root=lab/_claim_directory(continuation)
    # Stable scope identity prevents whitespace, metadata or bundle edits from
    # resetting the single approved campaign's ten-dollar lifetime allowance.
    claim_path=claim_root/(bundle['campaign_id']+'.json')
    if claim_path.exists():
        raise ValueError('continuation_already_claimed' if continuation is not None else 'campaign_already_claimed')
    env=Path(env_path or lab/'.env')
    from lab_paths import attach_devon
    attach_devon(Path(bundle['devon_root']))
    import run_lab
    validated=[]
    jobs_by_id={row['job_id']:row for row in bundle['jobs']}
    runnable=([jobs_by_id[identifier] for identifier in bundle['execution_job_ids']]
        if _recovery_phase(continuation)>=3 else bundle['jobs'])
    for job in runnable:
        policy,plan_path,approval_path,output_path=_policy_for(job,bundle,directory,env,lab)
        if output_path.exists():
            raise ValueError('campaign_output_exists')
        await run_lab._precheck(policy.plan,Path(bundle['devon_root']))
        validated.append((job,policy,plan_path,approval_path,output_path))
    # All prechecks precede all approvals/claims/network. Revalidate after capture work.
    for job,_,_,_,_ in validated:
        _policy_for(job,bundle,directory,env,lab)
    active_amount,active_attempts=_active_allowance(continuation)
    suffix='-continuation'+str(_recovery_phase(continuation)) if continuation is not None else ''
    budget=CostBudget(active_amount,active_attempts,approval_id='campaign-'+bundle['campaign_sha256']+suffix)
    ledger=_Ledger(directory/'ledger.json',budget,bundle)
    if _recovery_phase(continuation)>=3:
        for reused in continuation['reused_completed_outputs']:
            job=jobs_by_id[reused['job_id']]
            ledger.jobs.append({'job_id':job['job_id'],'model_id':job['model_id'],'experiment':job['experiment'],
                'cases_root':job['cases_root'],'run_state':'terminal_interrupted' if reused.get('partial_terminal') else 'completed',
                'output_path':job['output_path'],'expected_cases':job['expected_cases'],
                'recorded_cases':reused.get('original_recorded_cases',job['expected_cases']),
                'succeeded_cases':reused.get('succeeded_cases',job['expected_cases']),
                'failed_cases':reused.get('failed_cases',0),'source_failed_cases':reused.get('source_failed_cases',0),
                'original_recorded_cases':reused.get('original_recorded_cases',job['expected_cases']),
                'logical_terminal_cases':reused.get('logical_terminal_cases',job['expected_cases']),
                'terminal_failure_observations':reused.get('terminal_failure_observations',0),'reused':True,
                'source_output_path':reused['output_path'],'source_output_sha256':reused['output_sha256'],
                'source_directory':reused['source_directory']})
    context=CampaignContext(budget,campaign,bundle['campaign_sha256'],
        frozenset(row['plan_sha256'] for row in runnable),ledger.audit,continuation)
    for _,policy,_,_,_ in validated:
        context.validate(policy)
    claim_root.mkdir(parents=True,exist_ok=True)
    try:
        _write_new(claim_path,{'version':1,'campaign_id':bundle['campaign_id'],
            'campaign_sha256':bundle['campaign_sha256'],'bundle_sha256':file_sha256(Path(bundle_path)),
            'budget_usd_total':'10.00','max_http_attempts_total':192,'claimed_at':datetime.now(timezone.utc).isoformat(),
            'active_budget_usd':format(active_amount,'f'),'active_max_http_attempts':active_attempts,
            'continuation':continuation})
    except FileExistsError:
        raise ValueError('continuation_already_claimed' if continuation is not None else 'campaign_already_claimed') from None
    ledger.save()
    executor=execute_plan or run_lab.execute_approved_plan
    error=None
    try:
        for job,_,plan_path,approval_path,output_path in validated:
            if budget.to_dict()['halted']:
                ledger.state='budget_stopped'
                break
            ledger.current_job_id=job['job_id']
            ledger.save()
            result=await executor(plan_path,approval_path,env,output_path,campaign_context=context)
            rows=result.get('cases',[])
            ledger.jobs.append({'job_id':job['job_id'],'model_id':job['model_id'],
                'experiment':job['experiment'],'cases_root':job['cases_root'],'run_state':result.get('run_state'),
                'output_path':job['output_path'],'expected_cases':job['expected_cases'],
                'recorded_cases':len(rows),'succeeded_cases':sum(row.get('status')=='succeeded' for row in rows),
                'failed_cases':sum(row.get('status') in {'failed','rejected'} for row in rows)})
            ledger.save()
            if budget.to_dict()['halted'] or result.get('run_state') in {'budget_stopped','failed','interrupted'}:
                ledger.state='budget_stopped' if budget.to_dict()['halted'] or result.get('run_state')=='budget_stopped' else result['run_state']
                break
        else:
            ledger.state='completed'
    except BaseException as exc:
        ledger.state='interrupted' if isinstance(exc,(KeyboardInterrupt,__import__('asyncio').CancelledError)) else 'failed'
        error='campaign_interrupted' if ledger.state=='interrupted' else 'campaign_execution_rejected'
    finally:
        ledger.current_job_id=None
        ledger.save()
    settled=[row for row in ledger.events if row.get('event')=='settled']
    exact=[Decimal(row['cost_usd']) for row in settled if row.get('cost_usd') is not None]
    bounded=[row for row in settled if row.get('cost_usd') is None and row.get('cost_upper_usd') is not None]
    inherited_exact=Decimal(continuation.get('inherited_confirmed_cost_known_subtotal_usd','0')) if continuation else Decimal(0)
    inherited_bounded=continuation.get('inherited_bounded_cost_attempts',0) if continuation else 0
    reused_cases=sum(row['recorded_cases'] for row in ledger.jobs if row.get('reused'))
    report={'campaign_id':bundle['campaign_id'],'run_state':ledger.state,'run_error':error,
        'global_budget':ledger.snapshot(),'jobs':ledger.jobs,'pending_jobs':18-len(ledger.jobs),
        'planned_model_case_pairs':96,'recorded_cases':sum(row['recorded_cases'] for row in ledger.jobs),
        'succeeded_cases':sum(row['succeeded_cases'] for row in ledger.jobs),
        'failed_cases':sum(row.get('source_failed_cases',row['failed_cases']) for row in ledger.jobs),
        'quality_denominator':0,'quality_evaluation':'diagnostic_only','review_status':'unreviewed',
        'confirmed_cost_known_subtotal_usd':format(sum(exact,inherited_exact),'f'),
        'bounded_cost_attempts':len(bounded)+inherited_bounded,'unconfirmed_attempts':budget.to_dict()['unknown_attempts'],
        'settled_attempts':len(settled),'automatic_resume':False,'continuation':continuation,
        'prior_first_case_retry':continuation is not None,'historical_unknown_first_case':continuation is not None}
    if continuation is not None:
        report['unconfirmed_attempts']+=continuation['inherited_unknown_attempts']
        report['active_settled_attempts']=report['settled_attempts']
        report['settled_attempts']+=continuation['inherited_attempts']
    if _recovery_phase(continuation)>=3:
        report['reused_cases']=reused_cases
        report['new_recorded_cases']=report['recorded_cases']-reused_cases
        report['reused_completed_job_ids']=deepcopy(continuation['reused_completed_job_ids'])
        report['execution_job_ids']=deepcopy(continuation['execution_job_ids'])
    if _recovery_phase(continuation)==4:
        observations=deepcopy(continuation['terminal_case_observations'])
        report['terminal_case_observations']=observations
        report['terminal_interrupted_observations']=len(observations)
        report['source_recorded_cases']=report['recorded_cases']
        report['logical_terminal_cases']=report['recorded_cases']+len(observations)
        report['logical_failed_cases']=report['failed_cases']+len(observations)
    _write_new(directory/'campaign-result.json',report)
    return report
