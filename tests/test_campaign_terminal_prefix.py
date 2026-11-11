"""The cancelled last Argon A case is an observation, never a fabricated model row."""
from __future__ import annotations
import asyncio
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch

import campaign_runtime as runtime
import test_campaign_completed_prefix as fixtures

REUSED=fixtures.REUSED+[f'gemini-3.8-flash-{n}' for n in (1,2,3)]+['gemini-4-argon-1']
ORDER=['gemini-4-argon-2','gemini-4-argon-3']+[f'{model}-{n}' for model in
    ('claude-haiku-5-5','gpt-6-luna','claude-sonnet-5-5') for n in (1,2,3)]


class CampaignTerminalPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helper=fixtures.CampaignCompletedPrefixTests
        helper.setUpClass();cls.addClassCleanup(helper.doClassCleanups)
        cls.root=helper.root;directory=cls.root/'runs/recovery3'
        phase3=runtime.prepare_continuation(helper.parent,directory,lab_root=cls.root)
        cls.parent=directory/'bundle.json'
        groups=[([Decimal('.01')]*12+[Decimal('.02024325'),Decimal('.0121785')]),
            [Decimal('.007')]*3+[Decimal('.00703200')],[Decimal('.0088785')],
            [Decimal('.01')]*17+[Decimal('.153750'),Decimal('.018'),Decimal('.018334')]]
        async def execute(plan_path,approval,env,output,*,campaign_context):
            plan=json.loads(plan_path.read_text(encoding='utf-8'));job=plan_path.stem
            index=['gemini-3.8-flash-1','gemini-3.8-flash-2','gemini-3.8-flash-3','gemini-4-argon-1'].index(job)
            for local,cost in enumerate(groups[index],1):
                ticket=campaign_context.budget.reserve(Decimal('.2'))
                event={'attempt_id':ticket,'local_attempt_id':f'attempt-{local}','model':plan['model_ids'][0],
                    'reserved_usd':'.2','plan_sha256':runtime.plan_digest(plan),'wire_protocol':'chat_completions'}
                campaign_context.audit_callback(dict(event,event='reserved'))
                campaign_context.budget.settle(ticket,cost)
                bounded=(index==0 and local==14) or (index==3 and local>=19)
                campaign_context.audit_callback(dict(event,event='settled',http_status=200,sent=True,
                    cost_status='bounded' if bounded else 'confirmed',cost_usd=None if bounded else str(cost),
                    cost_lower_usd='0' if bounded else str(cost),cost_upper_usd=str(cost)))
            ids=plan['selected_case_ids'];partial=index==3
            cases=[dict({'case':case+'.v1'} if plan['experiment']=='A' else {'case_id':case},
                status='failed' if index==0 and number>=3 else 'succeeded',review_status='unreviewed')
                for number,case in enumerate(ids[:10] if partial else ids)]
            result={'run_state':'budget_stopped' if partial else 'completed','cases':cases,
                'approval_plan_sha256':runtime.plan_digest(plan)}
            if partial:
                ticket=campaign_context.budget.reserve(Decimal('.080842'))
                event={'attempt_id':ticket,'local_attempt_id':'attempt-21','model':'gemini-4-argon',
                    'reserved_usd':'0.080842','plan_sha256':runtime.plan_digest(plan),'wire_protocol':'chat_completions'}
                campaign_context.audit_callback(dict(event,event='reserved'))
                campaign_context.budget.settle(ticket,None)
                campaign_context.audit_callback(dict(event,event='settled',http_status=None,sent=True,
                    cost_status='unconfirmed',cost_usd=None,cost_lower_usd=None,cost_upper_usd=None,
                    response_id=None,error_code='attempt_cancelled'))
                result['run_error']={'code':'attempt_cancelled'}
                result['checkpoint']={'completed':10,'total':11,'current_case':'a-dev-0025.v1'}
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(result),encoding='utf-8')
            return result
        with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
            asyncio.run(runtime.execute_campaign(cls.parent,lab_root=cls.root,execute_plan=execute))
        cls.preserved={str(path):path.read_bytes() for path in directory.rglob('*.json')}
        for relative in ('runs/.campaign-claims/dev-30pct-10usd.json','runs/.campaign-continuation-claims/dev-30pct-10usd.json',
                'runs/.campaign-recovery2-claims/dev-30pct-10usd.json','runs/.campaign-recovery3-claims/dev-30pct-10usd.json'):
            path=cls.root/relative;cls.preserved[str(path)]=path.read_bytes()

    def prepare(self,label):
        destination=self.root/'runs'/label
        return destination,runtime.prepare_continuation(self.parent,destination,lab_root=self.root)

    def test_01_exact_terminal_prefix_keeps_usage_unknown_and_only_eleven_jobs_runnable(self):
        directory,bundle=self.prepare('scope4');proof=bundle['continuation']
        self.assertEqual(proof['recovery_phase'],4)
        self.assertEqual(bundle['active_budget_usd'],'8.62187680')
        self.assertEqual(bundle['active_max_http_attempts'],122)
        self.assertEqual(proof['inherited_known_debited_upper_usd'],'1.07990845')
        self.assertEqual(proof['inherited_unknown_hold_usd'],'0.29821475')
        self.assertEqual(proof['inherited_budget_debit_usd'],'1.37812320')
        self.assertEqual(proof['inherited_attempts'],70)
        self.assertEqual(proof['inherited_unknown_attempts'],4)
        self.assertEqual(bundle['reused_completed_job_ids'],REUSED)
        self.assertEqual(bundle['execution_job_ids'],ORDER)
        jobs=[row for row in bundle['jobs'] if row['job_id'] in ORDER]
        self.assertEqual(sum(row['expected_cases'] for row in jobs),53)
        self.assertEqual(sum(row['max_http_attempts'] for row in jobs),106)
        self.assertEqual(sum(Decimal(row['budget_usd']) for row in jobs),Decimal('4.9875'))
        partial=next(row for row in proof['reused_completed_outputs'] if row['job_id']=='gemini-4-argon-1')
        self.assertTrue(partial['partial_terminal'])
        self.assertEqual(partial['original_recorded_cases'],10)
        self.assertEqual(len(partial['recorded_case_ids']),10)
        self.assertEqual(len(partial['selected_case_ids']),11)
        self.assertEqual(len(json.loads(Path(partial['output_path']).read_text())['cases']),10)
        terminal=proof['terminal_case_observations'][0]
        self.assertEqual(terminal['case_id'],'a-dev-0025')
        self.assertEqual(terminal['source_lifetime_attempt_id'],'attempt-70')
        self.assertEqual(terminal['status'],'interrupted')
        self.assertFalse(terminal['retry_planned'])
        self.assertTrue(all(terminal[key] is None for key in ('input_tokens','output_tokens','actual_cost_usd','output','http_status')))
        context=runtime.CampaignContext(runtime.CostBudget(Decimal('8.62187680'),122,approval_id='fake-phase4'),
            Path(bundle['campaign_path']),bundle['campaign_sha256'],frozenset(row['plan_sha256'] for row in bundle['jobs']),
            lambda event:None,proof)
        for job in [row for row in bundle['jobs'] if row['job_id'] in REUSED]:
            plan=json.loads((directory/job['plan_path']).read_text())
            policy=SimpleNamespace(lab_root=self.root,plan=plan,plan_sha256=runtime.plan_digest(plan),
                budget_usd=Decimal(plan['budget_usd']),max_http_attempts=plan['max_http_attempts'])
            with self.assertRaisesRegex(ValueError,'campaign_job_reused'):context.validate(policy)
        self.assertEqual(context.wire_protocol_for('gemini-4-argon'),'chat_completions')

    def test_02_only_cancelled_last_unrecorded_case_is_eligible(self):
        output=self.parent.parent/'results/gemini-4-argon-1.json';original=output.read_bytes()
        try:
            value=json.loads(original);value['checkpoint']['current_case']='a-dev-0022.v1'
            output.write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):self.prepare('wrongcase4')
        finally:output.write_bytes(original)

    def test_03_changed_partial_source_is_blocked_before_execution(self):
        directory,_=self.prepare('changed4');path=self.parent.parent/'results/gemini-4-argon-1.json';original=path.read_bytes()
        try:
            path.write_bytes(original+b'\n');execute=AsyncMock()
            with self.assertRaisesRegex(ValueError,'continuation_parent_changed'):
                asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
            execute.assert_not_called()
        finally:path.write_bytes(original)

    def test_04_execution_reuses_all_terminal_work_and_reports_ninetyfive_sdk_rows(self):
        directory,_=self.prepare('execute4');seen=[]
        async def execute(plan_path,approval,env,output,*,campaign_context):
            seen.append(plan_path.stem);plan=json.loads(plan_path.read_text())
            ticket=campaign_context.budget.reserve(Decimal('.001'))
            campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
            campaign_context.budget.settle(ticket,Decimal('.001'))
            campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':'.001','cost_upper_usd':'.001'})
            return {'run_state':'completed','cases':[{'case_id':case,'status':'succeeded'} for case in plan['selected_case_ids']]}
        with patch('run_lab._precheck',new=AsyncMock(return_value=None)) as precheck:
            result=asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
            self.assertEqual(precheck.await_count,11)
            self.assertEqual(seen,ORDER)
            self.assertEqual(result['run_state'],'completed')
            self.assertEqual(result['recorded_cases'],95)
            self.assertEqual(result['source_recorded_cases'],95)
            self.assertEqual(result['logical_terminal_cases'],96)
            self.assertEqual(result['terminal_interrupted_observations'],1)
            self.assertEqual(result['reused_cases'],42)
            self.assertEqual(result['new_recorded_cases'],53)
            self.assertEqual(result['failed_cases'],8)
            self.assertEqual(result['logical_failed_cases'],9)
            self.assertEqual(result['global_budget']['attempts_started'],81)
            self.assertEqual(result['global_budget']['unknown_attempts'],4)
            with self.assertRaisesRegex(ValueError,'continuation_already_claimed'):
                asyncio.run(runtime.execute_campaign(directory/'bundle.json',lab_root=self.root,execute_plan=execute))
        with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
            runtime.prepare_continuation(directory/'bundle.json',self.root/'runs/recovery5',lab_root=self.root)
        self.assertTrue(all(Path(path).read_bytes()==body for path,body in self.preserved.items()))


if __name__=='__main__':unittest.main()
