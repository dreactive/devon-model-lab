"""Recover the exact unsupported-text incident without repeating completed Sol cases."""
from __future__ import annotations
import asyncio
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock,patch

import campaign_runtime as runtime
from cost_accounting import CostBudget
import test_campaign_second_recovery as fixtures

LAB=Path(__file__).resolve().parents[1]
MESSAGE=('Unsupported parameter(s) for /v1/responses on this model: text. They cannot be honoured here '
    'and are rejected rather than ignored — remove them from the request.')
REUSED=['gpt-6.1-sol-1','gpt-6.1-sol-2','gpt-6.1-sol-3']
ORDER=[f'{model}-{number}' for model in ('gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5',
    'gpt-6-luna','claude-sonnet-5-5') for number in (1,2,3)]


class CampaignCompletedPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary=tempfile.TemporaryDirectory(dir=LAB/'runs')
        cls.addClassCleanup(temporary.cleanup)
        helper=fixtures.CampaignSecondRecoveryTests()
        cls.root,first_parent,_,_=helper.prepare_parent(temporary.name)
        directory=cls.root/'runs/recovery2'
        cls.phase2=runtime.prepare_continuation(first_parent,directory,lab_root=cls.root)
        cls.parent=directory/'bundle.json'
        cls.raw=directory/'results/gemini-3.8-flash-1-raw/response-0001.json'
        known=[Decimal('.02')]*12+[Decimal('.1030030')]+[Decimal('.01')]*13+[Decimal('.0574892')]
        index=0
        async def execute(plan_path,approval,env,output,*,campaign_context):
            nonlocal index
            plan=json.loads(plan_path.read_text(encoding='utf-8'))
            model=plan['model_ids'][0]
            if model=='gpt-6.1-sol':
                count=22 if plan['experiment']=='A' else len(plan['selected_case_ids'])
                for local in range(1,count+1):
                    cost=known[index];status='confirmed' if index<13 else 'bounded';index+=1
                    ticket=campaign_context.budget.reserve(Decimal('.15'))
                    event={'attempt_id':ticket,'local_attempt_id':f'attempt-{local}','model':model,
                        'reserved_usd':'.15','plan_sha256':runtime.plan_digest(plan)}
                    campaign_context.audit_callback(dict(event,event='reserved'))
                    campaign_context.budget.settle(ticket,cost)
                    campaign_context.audit_callback(dict(event,event='settled',http_status=200,sent=True,
                        cost_status=status,cost_usd=str(cost) if status=='confirmed' else None,
                        cost_lower_usd=str(cost) if status=='confirmed' else '0',cost_upper_usd=str(cost)))
                cases=[dict({'case':case+'.v1'} if plan['experiment']=='A' else {'case_id':case},
                    status='succeeded',review_status='unreviewed') for case in plan['selected_case_ids']]
                result={'run_state':'completed','cases':cases,'approval_plan_sha256':runtime.plan_digest(plan)}
            else:
                ticket=campaign_context.budget.reserve(Decimal('.02419275'))
                event={'attempt_id':ticket,'local_attempt_id':'attempt-1','model':model,
                    'reserved_usd':'0.02419275','plan_sha256':runtime.plan_digest(plan)}
                campaign_context.audit_callback(dict(event,event='reserved'))
                campaign_context.budget.settle(ticket,None)
                campaign_context.audit_callback(dict(event,event='settled',http_status=400,sent=True,
                    cost_status='unconfirmed',cost_usd=None,cost_lower_usd=None,cost_upper_usd=None,
                    response_id=None,error_code='response_usage_unconfirmed'))
                result={'run_state':'budget_stopped','cases':[],
                    'approval_plan_sha256':runtime.plan_digest(plan),'run_error':{'code':'response_usage_unconfirmed'}}
                raw={'error':{'message':MESSAGE,'type':'invalid_request_error','param':None,'code':'400'},
                    '_elice_diagnostic':{'kind':'http_error','http_status':400,'model':model,'attempt_id':ticket,
                        'captured_body_bytes':244,'body_sha256':'163efdfcb9029ebaf23b060bfd60d928d61f7bdc79a6db71a9cb698d801a7579',
                        'hash_scope':'captured_body_bytes','body_truncated':False,'body_kind':'json',
                        'error_code':'response_usage_unconfirmed'},
                    '_elice_billing':{'usage':None,'cost_usd':None,'cost_lower_usd':None,'cost_upper_usd':None,
                        'cost_status':'unconfirmed','canonical_model':model,'provider_model':None,
                        'attempt_id':ticket,'accounting_basis':'billing_upper_bound'}}
                cls.raw.parent.mkdir(parents=True,exist_ok=True)
                cls.raw.write_text(json.dumps(raw),encoding='utf-8')
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(result),encoding='utf-8')
            return result
        with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
            asyncio.run(runtime.execute_campaign(cls.parent,lab_root=cls.root,execute_plan=execute))
        cls.preserved={str(path):path.read_bytes() for path in directory.rglob('*.json')}
        for relative in ('runs/.campaign-claims/dev-30pct-10usd.json',
                'runs/.campaign-continuation-claims/dev-30pct-10usd.json',
                'runs/.campaign-recovery2-claims/dev-30pct-10usd.json'):
            path=cls.root/relative;cls.preserved[str(path)]=path.read_bytes()

    def prepare(self,label):
        destination=self.root/'runs'/label
        result=runtime.prepare_continuation(self.parent,destination,lab_root=self.root)
        return destination,result

    def test_01_scope_reuses_sixteen_cases_and_carries_separate_cost_categories(self):
        directory,bundle=self.prepare('scope3')
        proof=bundle['continuation']
        self.assertEqual(proof['recovery_phase'],3)
        self.assertEqual(proof['inherited_attempts'],30)
        self.assertEqual(proof['inherited_unknown_attempts'],3)
        self.assertEqual(proof['inherited_known_debited_upper_usd'],'0.5304922')
        self.assertEqual(proof['inherited_unknown_hold_usd'],'0.21737275')
        self.assertEqual(proof['inherited_budget_debit_usd'],'0.74786495')
        self.assertEqual(bundle['active_budget_usd'],'9.25213505')
        self.assertEqual(bundle['active_max_http_attempts'],162)
        self.assertEqual(bundle['reused_completed_job_ids'],REUSED)
        self.assertEqual(bundle['execution_job_ids'],ORDER)
        runnable=[row for row in bundle['jobs'] if row['job_id'] in ORDER]
        self.assertEqual(sum(Decimal(row['budget_usd']) for row in runnable),Decimal('7.47580725'))
        self.assertEqual(sum(row['max_http_attempts'] for row in runnable),159)
        self.assertEqual(sum(row['expected_cases'] for row in runnable),80)
        self.assertEqual(sum(row['expected_cases'] for row in bundle['jobs']),96)
        context=runtime.CampaignContext(CostBudget(Decimal('9.25213505'),162,approval_id='fake-phase3'),Path(bundle['campaign_path']),
            bundle['campaign_sha256'],frozenset(row['plan_sha256'] for row in runnable),lambda event:None,proof)
        self.assertEqual(context.wire_protocol_for('gpt-6-luna'),'responses')
        self.assertEqual(context.wire_protocol_for('gpt-6.1-sol'),'responses')
        for model in ('gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5'):
            self.assertEqual(context.wire_protocol_for(model),'chat_completions')
        reused=bundle['jobs'][0]
        plan=json.loads((directory/reused['plan_path']).read_text(encoding='utf-8'))
        policy=SimpleNamespace(lab_root=self.root,plan=plan,plan_sha256=runtime.plan_digest(plan),
            budget_usd=Decimal(plan['budget_usd']),max_http_attempts=plan['max_http_attempts'])
        broad_context=runtime.CampaignContext(context.budget,context.campaign_path,context.campaign_sha256,
            frozenset(row['plan_sha256'] for row in bundle['jobs']),context.audit_callback,proof)
        with self.assertRaisesRegex(ValueError,'campaign_job_reused'):
            broad_context.validate(policy)
        self.assertEqual(len(proof['reused_completed_outputs']),3)
        self.assertTrue(all(Path(row['output_path']).is_file() for row in proof['reused_completed_outputs']))
        self.assertTrue(all(Path(path).read_bytes()==body for path,body in self.preserved.items()))

    def test_02_completed_output_and_incident_must_remain_exact(self):
        paths=[self.parent.parent/'results/gpt-6.1-sol-1.json',self.raw]
        for number,path in enumerate(paths):
            original=path.read_bytes()
            try:
                value=json.loads(original)
                if number==0:value['cases'][0]['status']='failed'
                else:value['error']['message']='another unsupported parameter'
                path.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
                    self.prepare(f'tampered3-{number}')
            finally:path.write_bytes(original)

    def test_03_changed_completed_prefix_blocks_before_execution(self):
        directory,_=self.prepare('changed3')
        path=self.parent.parent/'results/gpt-6.1-sol-1.json';original=path.read_bytes()
        try:
            path.write_bytes(original+b'\n')
            execute=AsyncMock()
            with self.assertRaisesRegex(ValueError,'continuation_parent_changed'):
                asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
            execute.assert_not_called()
        finally:path.write_bytes(original)

    def test_04_no_completed_case_is_called_and_new_unknown_stops_everything(self):
        directory,_=self.prepare('execute3');seen=[]
        async def execute(plan,approval,env,output,*,campaign_context):
            seen.append(plan.stem)
            self.assertEqual(campaign_context.budget.amount_usd,Decimal('9.25213505'))
            self.assertEqual(campaign_context.budget.max_attempts,162)
            ticket=campaign_context.budget.reserve(Decimal('.05'))
            campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
            campaign_context.budget.settle(ticket,None)
            campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':None})
            return {'run_state':'budget_stopped','cases':[]}
        with patch('run_lab._precheck',new=AsyncMock(return_value=None)) as precheck:
            result=asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
            self.assertEqual(precheck.await_count,15)
            self.assertEqual(seen,['gemini-3.8-flash-1'])
            self.assertEqual(result['recorded_cases'],16)
            self.assertEqual(result['succeeded_cases'],16)
            self.assertEqual(result['reused_cases'],16)
            self.assertEqual(result['new_recorded_cases'],0)
            self.assertEqual(result['global_budget']['attempts_started'],31)
            self.assertEqual(result['global_budget']['unknown_attempts'],4)
            self.assertEqual(result['global_budget']['debited_upper_usd'],'0.74786495')
            self.assertEqual(result['confirmed_cost_known_subtotal_usd'],'0.3430030')
            self.assertEqual(result['bounded_cost_attempts'],14)
            self.assertEqual(result['settled_attempts'],31)
            self.assertEqual(sum(row.get('reused') is True for row in result['jobs']),3)
            self.assertTrue(all(row['source_output_path'] for row in result['jobs'] if row.get('reused')))
            with self.assertRaisesRegex(ValueError,'continuation_already_claimed'):
                asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
        ledger=json.loads((directory/'ledger.json').read_text())
        self.assertEqual(ledger['events'][0]['lifetime_attempt_id'],'attempt-31')
        with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
            runtime.prepare_continuation(directory/'bundle.json',self.root/'runs/recovery4',lab_root=self.root)
        self.assertTrue(all(Path(path).read_bytes()==body for path,body in self.preserved.items()))


if __name__=='__main__':unittest.main()
