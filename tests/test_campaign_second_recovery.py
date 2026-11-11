"""A second recovery recognizes only the provider's recorded non-streaming cap error."""
from __future__ import annotations
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock,patch

import campaign_runtime as runtime
import test_campaign_continuation as fixtures

LAB=Path(__file__).resolve().parents[1]
MESSAGE=('max_output_tokens 4096 exceeds the 2000-token ceiling this proxy holds a NON-STREAMING reply to: '
    'the answer is invisible until it finishes and the gateway kills a long one mid-generation, so a larger '
    'budget would buy a timeout rather than a longer answer. Send stream=true for the full length, or lower '
    'max_output_tokens to 2000 or less.')


class CampaignSecondRecoveryTests(unittest.TestCase):
    def prepare_parent(self,directory):
        helper=fixtures.CampaignContinuationTests()
        root,original,preserved=helper.prepare_parent(directory)
        destination=root/'runs/continuation1'
        phase1=runtime.prepare_continuation(original,destination,lab_root=root)
        first=phase1['jobs'][0]
        raw_path=destination/'results/gpt-6.1-sol-1-raw/response-0001.json'
        raw={'error':{'message':MESSAGE,'type':'invalid_request_error','param':None,'code':'400'},
            '_elice_diagnostic':{'kind':'http_error','http_status':400,'model':'gpt-6.1-sol',
                'attempt_id':'attempt-1','captured_body_bytes':418,
                'body_sha256':'45ed0abe894f198cc35984c66f3ae3fa274e38dba16fb98b811c81db3e5f45df',
                'hash_scope':'captured_body_bytes','body_truncated':False,'body_kind':'json',
                'error_code':'response_usage_unconfirmed'},
            '_elice_billing':{'usage':None,'cost_usd':None,'cost_lower_usd':None,'cost_upper_usd':None,
                'cost_status':'unconfirmed','canonical_model':'gpt-6.1-sol','provider_model':None,
                'attempt_id':'attempt-1','accounting_basis':'billing_upper_bound'}}
        async def execute(plan,approval,env,output,*,campaign_context):
            ticket=campaign_context.budget.reserve(Decimal('.09659'))
            event={'attempt_id':ticket,'local_attempt_id':'attempt-1','model':'gpt-6.1-sol',
                'reserved_usd':'0.09659','plan_sha256':first['plan_sha256']}
            campaign_context.audit_callback(dict(event,event='reserved'))
            campaign_context.budget.settle(ticket,None)
            campaign_context.audit_callback(dict(event,event='settled',http_status=400,sent=True,
                cost_status='unconfirmed',error_code='response_usage_unconfirmed',cost_usd=None,
                cost_lower_usd=None,cost_upper_usd=None,response_id=None))
            result={'run_state':'budget_stopped','cases':[],
                'run_error':{'code':'response_usage_unconfirmed'},'approval_plan_sha256':first['plan_sha256']}
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(result),encoding='utf-8')
            raw_path.parent.mkdir(parents=True,exist_ok=True)
            raw_path.write_text(json.dumps(raw),encoding='utf-8')
            return result
        with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
            asyncio.run(runtime.execute_campaign(destination/'bundle.json',lab_root=root,execute_plan=execute))
        evidence=[destination/'bundle.json',destination/'ledger.json',destination/'campaign-result.json',
            destination/first['output_path'],raw_path,
            root/'runs/.campaign-continuation-claims/dev-30pct-10usd.json']
        preserved.update({str(path):path.read_bytes() for path in evidence})
        return root,destination/'bundle.json',raw_path,preserved

    def test_second_recovery_preserves_two_holds_and_sets_all_model_caps_to_2000(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,raw,preserved=self.prepare_parent(directory)
            result=runtime.prepare_continuation(parent,root/'runs/recovery2',lab_root=root)
            proof=result['continuation']
            self.assertEqual(proof['recovery_phase'],2)
            self.assertEqual(proof['inherited_unknown_hold_usd'],'0.19318')
            self.assertEqual(proof['inherited_attempts'],2)
            self.assertEqual(proof['inherited_unknown_attempts'],2)
            self.assertEqual(len(proof['parent_directories']),2)
            self.assertEqual(proof['parent_raw_sha256'],runtime.file_sha256(raw))
            self.assertEqual(result['active_budget_usd'],'9.80682')
            self.assertEqual(result['active_max_http_attempts'],190)
            self.assertEqual(sum(Decimal(row['budget_usd']) for row in result['jobs']),Decimal('9.80682'))
            self.assertEqual(sum(row['max_http_attempts'] for row in result['jobs']),190)
            self.assertEqual(sum(row['expected_cases'] for row in result['jobs']),96)
            jobs={row['job_id']:row for row in result['jobs']}
            self.assertEqual(jobs['gpt-6.1-sol-1']['budget_usd'],'1.52557')
            self.assertEqual(jobs['gpt-6.1-sol-1']['max_http_attempts'],22)
            self.assertEqual(jobs['gpt-6.1-sol-2']['max_http_attempts'],6)
            for job in result['jobs']:
                plan=json.loads((root/'runs/recovery2'/job['plan_path']).read_text())
                self.assertEqual(plan['limits']['max_output_tokens'],2000)
                self.assertFalse(plan['limits']['stream'])
            for model in runtime.MODELS:
                manifest=json.loads((root/'runs/recovery2/manifests'/f'{model}.json').read_text())
                self.assertEqual(manifest['limits']['max_output_tokens'],2000)
                self.assertFalse(manifest['limits']['stream'])
                for overrides in manifest.get('task_limits',{}).values():
                    if 'max_output_tokens' in overrides:self.assertEqual(overrides['max_output_tokens'],2000)
                    if 'stream' in overrides:self.assertFalse(overrides['stream'])
            self.assertTrue(all(Path(path).read_bytes()==body for path,body in preserved.items()))

    def test_other_provider_errors_or_positive_usage_do_not_qualify(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,raw,_=self.prepare_parent(directory)
            original=json.loads(raw.read_text())
            for label in ('message','param','status','usage'):
                value=json.loads(json.dumps(original))
                if label=='message':value['error']['message']='some other 400 error'
                elif label=='param':value['error']['param']='max_output_tokens'
                elif label=='status':value['_elice_diagnostic']['http_status']=429
                else:value['_elice_billing']['usage']={'input_tokens':1}
                raw.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
                    runtime.prepare_continuation(parent,root/'runs'/label,lab_root=root)

    def test_new_unknown_stops_at_lifetime_three_and_no_third_recovery_exists(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,_,preserved=self.prepare_parent(directory)
            destination=root/'runs/recovery2'
            runtime.prepare_continuation(parent,destination,lab_root=root)
            seen=[]
            async def execute(plan,approval,env,output,*,campaign_context):
                seen.append(plan)
                ticket=campaign_context.budget.reserve(Decimal('.05'))
                campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
                campaign_context.budget.settle(ticket,None)
                campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':None})
                return {'run_state':'budget_stopped','cases':[]}
            with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
                result=asyncio.run(runtime.execute_campaign(destination/'bundle.json',lab_root=root,execute_plan=execute))
                self.assertEqual(len(seen),1)
                self.assertEqual(result['global_budget']['attempts_started'],3)
                self.assertEqual(result['global_budget']['unknown_attempts'],3)
                self.assertEqual(result['global_budget']['inherited_unknown_hold_usd'],'0.19318')
                self.assertEqual(result['settled_attempts'],3)
                self.assertEqual(result['run_state'],'budget_stopped')
                with self.assertRaisesRegex(ValueError,'continuation_already_claimed'):
                    asyncio.run(runtime.execute_campaign(destination/'bundle.json',lab_root=root,execute_plan=execute))
            with self.assertRaisesRegex(ValueError,'continuation_parent_not_eligible'):
                runtime.prepare_continuation(destination/'bundle.json',root/'runs/recovery3',lab_root=root)
            ledger=json.loads((destination/'ledger.json').read_text())
            self.assertEqual(ledger['events'][0]['lifetime_attempt_id'],'attempt-3')
            self.assertTrue(all(Path(path).read_bytes()==body for path,body in preserved.items()))

    def test_changed_raw_error_is_rejected_before_any_execution(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root,parent,raw,_=self.prepare_parent(directory)
            destination=root/'runs/recovery2'
            runtime.prepare_continuation(parent,destination,lab_root=root)
            with raw.open('a',encoding='utf-8') as stream:stream.write('\n')
            execute=AsyncMock()
            with self.assertRaisesRegex(ValueError,'continuation_parent_changed'):
                asyncio.run(runtime.execute_campaign(destination/'bundle.json',lab_root=root,execute_plan=execute))
            execute.assert_not_called()


if __name__=='__main__':unittest.main()
