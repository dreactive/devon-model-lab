"""Only the explicitly waived first unpriced 404 may be carried as a hold."""
from __future__ import annotations
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock,patch

import campaign_runtime as runtime
import test_campaign_runtime as fixtures

LAB=Path(__file__).resolve().parents[1]


class CampaignContinuationTests(unittest.TestCase):
    def prepare_parent(self,directory):
        helper=fixtures.CampaignExecutionTests()
        runtime,root,bundle=helper.prepare(directory)
        body=json.loads(bundle.read_text(encoding='utf-8'))
        first=body['jobs'][0]
        budget={'amount_usd':'10','max_attempts':192,'attempts_started':1,'reserved_usd':'0',
            'remaining_usd':None,'unknown_attempts':1,'in_flight_attempts':0,'halted':True,
            'halt_reason':'actual_cost_unconfirmed','debited_upper_usd':'0'}
        ledger={'version':1,'campaign_id':'dev-30pct-10usd','run_state':'budget_stopped','global_budget':budget,
            'current_job_id':None,'jobs':[{'job_id':first['job_id'],'model_id':first['model_id'],
                'run_state':'budget_stopped','recorded_cases':0,'succeeded_cases':0,'failed_cases':0}],
            'events':[{'event':'reserved','attempt_id':'attempt-1','local_attempt_id':'attempt-1',
                'model':'gpt-6.1-sol','reserved_usd':'0.09659','job_id':first['job_id'],'plan_sha256':first['plan_sha256']},
                {'event':'settled','attempt_id':'attempt-1','local_attempt_id':'attempt-1','model':'gpt-6.1-sol',
                 'reserved_usd':'0.09659','cost_usd':None,'cost_lower_usd':None,'cost_upper_usd':None,
                 'cost_status':'unconfirmed','error_code':'response_usage_unconfirmed','http_status':404,'sent':True,
                 'response_id':None,'job_id':first['job_id'],'plan_sha256':first['plan_sha256']}]}
        result={'campaign_id':'dev-30pct-10usd','run_state':'budget_stopped','global_budget':budget,
            'recorded_cases':0,'succeeded_cases':0,'failed_cases':0,'unconfirmed_attempts':1,'jobs':ledger['jobs']}
        for name,value in [('ledger.json',ledger),('campaign-result.json',result)]:
            (bundle.parent/name).write_text(json.dumps(value),encoding='utf-8')
        first_output=bundle.parent/first['output_path']
        first_output.parent.mkdir(parents=True,exist_ok=True)
        first_output.write_text(json.dumps({'run_state':'budget_stopped','cases':[],
            'run_error':{'code':'response_usage_unconfirmed'},'approval_plan_sha256':first['plan_sha256']}),encoding='utf-8')
        claims=root/'runs/.campaign-claims';claims.mkdir()
        claim=claims/'dev-30pct-10usd.json'
        claim.write_text(json.dumps({'version':1,'campaign_id':body['campaign_id'],
            'campaign_sha256':body['campaign_sha256'],'bundle_sha256':runtime.file_sha256(bundle),
            'budget_usd_total':'10.00','max_http_attempts_total':192}),encoding='utf-8')
        preserved={str(p):p.read_bytes() for p in [bundle,bundle.parent/'ledger.json',bundle.parent/'campaign-result.json',first_output,claim]}
        return root,bundle,preserved

    def test_explicit_continuation_retains_hold_and_reallocates_one_retry(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,preserved=self.prepare_parent(directory)
            result=runtime.prepare_continuation(parent,root/'runs/continuation',lab_root=root)
            proof=result['continuation']
            self.assertEqual(proof['inherited_unknown_hold_usd'],'0.09659')
            self.assertEqual(result['active_budget_usd'],'9.90341')
            self.assertEqual(result['active_max_http_attempts'],191)
            self.assertEqual(sum(Decimal(j['budget_usd']) for j in result['jobs']),Decimal('9.90341'))
            self.assertEqual(sum(j['max_http_attempts'] for j in result['jobs']),191)
            jobs={j['job_id']:j for j in result['jobs']}
            self.assertEqual(jobs['gpt-6.1-sol-1']['budget_usd'],'1.62216')
            self.assertEqual(jobs['gpt-6.1-sol-1']['max_http_attempts'],22)
            self.assertEqual(jobs['gpt-6.1-sol-2']['max_http_attempts'],7)
            self.assertEqual(sum(j['expected_cases'] for j in result['jobs']),96)
            self.assertTrue(all(Path(p).read_bytes()==raw for p,raw in preserved.items()))

    def test_paid_or_completed_or_second_attempt_parent_cannot_be_waived(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,_=self.prepare_parent(directory)
            path=parent.parent/'ledger.json';original=json.loads(path.read_text())
            for name in ['paid','completed','second_attempt']:
                value=json.loads(json.dumps(original))
                if name=='paid':value['events'][1]['cost_usd']='0.01'
                elif name=='completed':value['jobs'][0]['recorded_cases']=1
                else:value['global_budget']['attempts_started']=2
                path.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
                    runtime.prepare_continuation(parent,root/'runs'/name,lab_root=root)
            path.write_text(json.dumps(original),encoding='utf-8')

    def test_new_unknown_stops_and_lifetime_counters_include_the_first404(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,preserved=self.prepare_parent(directory)
            new=root/'runs/continuation'
            runtime.prepare_continuation(parent,new,lab_root=root)
            seen=[]
            async def execute(plan,approval,env,output,*,campaign_context):
                seen.append(plan)
                self.assertEqual(campaign_context.budget.amount_usd,Decimal('9.90341'))
                self.assertEqual(campaign_context.budget.max_attempts,191)
                ticket=campaign_context.budget.reserve(Decimal('.1'))
                campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
                campaign_context.budget.settle(ticket,None)
                campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':None})
                return {'run_state':'budget_stopped','cases':[]}
            with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
                result=asyncio.run(runtime.execute_campaign(new/'bundle.json',lab_root=root,execute_plan=execute))
                self.assertEqual(len(seen),1)
                self.assertEqual(result['global_budget']['amount_usd'],'10')
                self.assertEqual(result['global_budget']['max_attempts'],192)
                self.assertEqual(result['global_budget']['attempts_started'],2)
                self.assertEqual(result['global_budget']['unknown_attempts'],2)
                self.assertEqual(result['global_budget']['inherited_unknown_hold_usd'],'0.09659')
                self.assertEqual(result['run_state'],'budget_stopped')
                with self.assertRaisesRegex(ValueError,'continuation_already_claimed'):
                    asyncio.run(runtime.execute_campaign(new/'bundle.json',lab_root=root,execute_plan=execute))
            self.assertTrue(all(Path(p).read_bytes()==raw for p,raw in preserved.items()))
            ledger=json.loads((new/'ledger.json').read_text(encoding='utf-8'))
            self.assertEqual(ledger['events'][0]['lifetime_attempt_id'],'attempt-2')

    def test_parent_edit_after_preparation_prevents_network(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,_=self.prepare_parent(directory)
            new=root/'runs/continuation'
            runtime.prepare_continuation(parent,new,lab_root=root)
            with (parent.parent/'ledger.json').open('a',encoding='utf-8') as stream:stream.write('\n')
            execute=AsyncMock()
            with self.assertRaisesRegex(ValueError,'continuation_parent_changed'):
                asyncio.run(runtime.execute_campaign(new/'bundle.json',lab_root=root,execute_plan=execute))
            execute.assert_not_called()
