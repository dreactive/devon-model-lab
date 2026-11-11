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
from execution_policy import build_plan, plan_digest, read_json, validate_execution

LAB_ROOT=Path(__file__).resolve().parent
MODELS=('gpt-6.1-sol','gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5','gpt-6-luna')
SELECTION='selections/dev-30pct-v1.json'
SELECTION_SHA256='f3dc03a866c9e5d299ff5f6860252ef763ecaeb879d80f1d3f0c22b18aa4bfd5'
ROOTS=(('A','cases/question/benchmark-v1',22,11),('B','cases/answer/main-v1',8,4),('B','cases/answer/legacy-na-v1',2,1))
BASE_RATES={'gpt-6.1-sol':('2','10'),'gemini-3.8-flash':('.75','3.75'),'gemini-4-argon':('2','10'),
            'claude-haiku-5-5':('.10','.50'),'claude-sonnet-5-5':('2','10'),'gpt-6-luna':('.10','.50')}
ATTACHMENT=Path('C:/Users/dreac/.codex/attachments/e31e678c-2597-49bf-b01d-0f234bfdb547/붙여넣은 텍스트.txt')
ATTACHMENT_SHA256='b192518d816ae1568fe75eb28ba70091bc90d5e76caae4940cfe47352f35e095'


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

    def validate(self,policy) -> None:
        if (type(self.budget) is not CostBudget or self.budget.amount_usd!=Decimal('10')
                or self.budget.max_attempts!=192 or not callable(self.audit_callback)
                or policy.plan_sha256 not in self.plan_sha256s
                or plan_digest(policy.plan)!=policy.plan_sha256):
            raise ValueError('campaign_context_invalid')
        root=Path(policy.lab_root).resolve()
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
        model=next(row for row in config['models'] if row['model_id']==models[0])
        relative=Path(policy.plan['config']['cases_path']).resolve().relative_to(root).as_posix()
        job=next((row for row in model['jobs'] if row['cases_root']==relative),None)
        if (job is None or policy.plan['experiment']!=job['experiment']
                or policy.budget_usd!=_amount(job['budget_usd'])
                or policy.max_http_attempts!=job['max_http_attempts']):
            raise ValueError('campaign_job_invalid')
        if self.budget.to_dict()['halted']:
            raise BudgetRejected('campaign_budget_halted')


def prepare_campaign(devon_root: Path,campaign_path: Path,output_dir: Path,*,
                     env_path: Path|None=None,lab_root: Path|None=None) -> dict:
    """Prepare a new one-shot, content-pinned bundle; no model or HTTP calls."""
    lab=Path(lab_root or LAB_ROOT).resolve()
    devon=Path(devon_root).resolve()
    campaign=_inside(campaign_path,lab/'campaigns')
    destination=_inside(output_dir,lab/'runs')
    if destination.exists() or destination.is_relative_to(devon):
        raise ValueError('campaign_output_exists_or_invalid')
    config=validate_campaign_config(read_json(campaign))
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
        manifest['limits']['max_output_tokens']=4096
        manifest['limits']['stream']=False
        for overrides in manifest.get('task_limits',{}).values():
            if 'max_input_bytes' in overrides:overrides['max_input_bytes']=65536
            if 'max_output_tokens' in overrides:overrides['max_output_tokens']=4096
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
    validate_campaign_config(read_json(campaign))
    if file_sha256(campaign)!=bundle['campaign_sha256'] or file_sha256(lab/SELECTION)!=SELECTION_SHA256:
        raise ValueError('campaign_bundle_changed')
    if (sum(_amount(row['budget_usd']) for row in bundle['jobs'])!=Decimal('10')
            or sum(row['max_http_attempts'] for row in bundle['jobs'])!=192
            or sum(row['expected_cases'] for row in bundle['jobs'])!=96):
        raise ValueError('campaign_bundle_invalid')
    expected={(model,kind,relative) for model in MODELS for kind,relative,_,_ in ROOTS}
    actual=[(row['model_id'],row['experiment'],row['cases_root']) for row in bundle['jobs']]
    if len(set(actual))!=18 or set(actual)!=expected:
        raise ValueError('campaign_bundle_scope_changed')
    expected_sizes={relative:count for _,relative,_,count in ROOTS}
    expected_caps={relative:cap for _,relative,cap,_ in ROOTS}
    for key in ('plan_path','approval_path','output_path','plan_sha256'):
        values=[row[key] for row in bundle['jobs']]
        if any(type(value) is not str or not value for value in values) or len(set(values))!=18:
            raise ValueError('campaign_bundle_scope_changed')
    for row in bundle['jobs']:
        if (row['expected_cases']!=expected_sizes[row['cases_root']]
                or row['max_http_attempts']!=expected_caps[row['cases_root']]):
            raise ValueError('campaign_bundle_scope_changed')
    return bundle,path.parent


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
        state['debited_upper_usd']=state.pop('spent_usd')
        state['accounting_basis']='conservative billing upper-bound debits, not confirmed invoice cost'
        return state

    def save(self):
        _atomic(self.path,{'version':1,'campaign_id':self.bundle['campaign_id'],'run_state':self.state,
            'global_budget':self.snapshot(),'current_job_id':self.current_job_id,'jobs':self.jobs,'events':self.events})

    def audit(self,event:dict):
        with self.lock:
            row=deepcopy(event)
            row['job_id']=self.current_job_id
            self.events.append(row)
            self.save() # synchronous durable write; failure propagates before HTTP.


async def execute_campaign(bundle_path:Path,*,env_path:Path|None=None,lab_root:Path|None=None,
                           execute_plan=None) -> dict:
    """Run one never-resumed campaign after all prechecks; stop globally on unknown usage."""
    lab=Path(lab_root or LAB_ROOT).resolve()
    bundle,directory=_bundle(Path(bundle_path),lab)
    campaign=Path(bundle['campaign_path'])
    claim_root=lab/'runs/.campaign-claims'
    # Stable scope identity prevents whitespace, metadata or bundle edits from
    # resetting the single approved campaign's ten-dollar lifetime allowance.
    claim_path=claim_root/(bundle['campaign_id']+'.json')
    if claim_path.exists():
        raise ValueError('campaign_already_claimed')
    env=Path(env_path or lab/'.env')
    from lab_paths import attach_devon
    attach_devon(Path(bundle['devon_root']))
    import run_lab
    validated=[]
    for job in bundle['jobs']:
        policy,plan_path,approval_path,output_path=_policy_for(job,bundle,directory,env,lab)
        if output_path.exists():
            raise ValueError('campaign_output_exists')
        await run_lab._precheck(policy.plan,Path(bundle['devon_root']))
        validated.append((job,policy,plan_path,approval_path,output_path))
    # All prechecks precede all approvals/claims/network. Revalidate after capture work.
    for job,_,_,_,_ in validated:
        _policy_for(job,bundle,directory,env,lab)
    budget=CostBudget(Decimal('10'),192,approval_id='campaign-'+bundle['campaign_sha256'])
    ledger=_Ledger(directory/'ledger.json',budget,bundle)
    context=CampaignContext(budget,campaign,bundle['campaign_sha256'],
        frozenset(row['plan_sha256'] for row in bundle['jobs']),ledger.audit)
    for _,policy,_,_,_ in validated:
        context.validate(policy)
    claim_root.mkdir(parents=True,exist_ok=True)
    try:
        _write_new(claim_path,{'version':1,'campaign_id':bundle['campaign_id'],
            'campaign_sha256':bundle['campaign_sha256'],'bundle_sha256':file_sha256(Path(bundle_path)),
            'budget_usd_total':'10.00','max_http_attempts_total':192,'claimed_at':datetime.now(timezone.utc).isoformat()})
    except FileExistsError:
        raise ValueError('campaign_already_claimed') from None
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
    report={'campaign_id':bundle['campaign_id'],'run_state':ledger.state,'run_error':error,
        'global_budget':ledger.snapshot(),'jobs':ledger.jobs,'pending_jobs':18-len(ledger.jobs),
        'planned_model_case_pairs':96,'recorded_cases':sum(row['recorded_cases'] for row in ledger.jobs),
        'succeeded_cases':sum(row['succeeded_cases'] for row in ledger.jobs),'failed_cases':sum(row['failed_cases'] for row in ledger.jobs),
        'quality_denominator':0,'quality_evaluation':'diagnostic_only','review_status':'unreviewed',
        'confirmed_cost_known_subtotal_usd':format(sum(exact,Decimal(0)),'f'),
        'bounded_cost_attempts':len(bounded),'unconfirmed_attempts':budget.to_dict()['unknown_attempts'],
        'settled_attempts':len(settled),'automatic_resume':False}
    _write_new(directory/'campaign-result.json',report)
    return report
