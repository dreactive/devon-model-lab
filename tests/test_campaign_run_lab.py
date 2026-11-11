"""Campaign-bound plans cannot bypass global accounting via the single runner."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decimal import Decimal

import httpx
import run_lab
import test_run_lab as fixtures

LAB=Path(__file__).resolve().parents[1]


class CampaignRunLabTests(unittest.TestCase):
    def test_campaign_plan_requires_context_before_reading_credentials(self):
        helper=fixtures.RunnerTests()
        with tempfile.TemporaryDirectory(dir=LAB/'tests') as directory:
            root,plan,approval,env=helper.prepare(directory,'B')
            value=json.loads(plan.read_text())
            value['config']['campaign_path']=str(root/'campaign.json')
            plan.write_text(json.dumps(value),encoding='utf-8')
            with patch.object(run_lab,'_credentials',side_effect=AssertionError('must reject before credentials')):
                with self.assertRaisesRegex(ValueError,'campaign_context_required'):
                    helper.execute(run_lab,root,plan,approval,env,httpx.MockTransport(lambda _:None))

    def test_raw_redaction_removes_key_values_and_named_secret_fields(self):
        value={'message':'contains FAKE_TOKEN_123','nested':{'api_key':'FAKE_OTHER','text':'normal'},'authorization':'Bearer FAKE_TOKEN_123'}
        clean=run_lab._redact_provider_json(value,'FAKE_TOKEN_123')
        self.assertNotIn('FAKE_TOKEN_123',json.dumps(clean))
        self.assertNotIn('FAKE_OTHER',json.dumps(clean))
        self.assertEqual(clean['nested']['text'],'normal')

    def test_actual_campaign_b_path_uses_shared_budget_and_redacts_all_evidence(self):
        from campaign_runtime import prepare_campaign, CampaignContext
        from cost_accounting import CostBudget
        import shutil
        helper=fixtures.RunnerTests()
        with tempfile.TemporaryDirectory(dir=LAB/'tests') as directory:
            root,_,_,env=helper.prepare(directory,'B')
            shutil.copytree(LAB/'campaigns',root/'campaigns')
            shutil.copytree(LAB/'selections',root/'selections')
            output_dir=root/'runs/campaign-fixture'
            bundle=prepare_campaign(Path('C:/Users/dreac/Desktop/kdt/devon'),root/'campaigns/dev-30pct-10usd.json',output_dir,
                env_path=env,lab_root=root)
            job=next(row for row in bundle['jobs'] if row['job_id']=='gpt-6-luna-2')
            budget=CostBudget(Decimal('10'),192,approval_id='offline-campaign')
            events=[]
            context=CampaignContext(budget,root/'campaigns/dev-30pct-10usd.json',bundle['campaign_sha256'],
                frozenset(row['plan_sha256'] for row in bundle['jobs']),events.append)
            sent=[]
            fake_key='FAKE_OFFLINE_KEY_NEVER_LOG_481'
            def respond(request):
                payload=json.loads(json.loads(request.content)['input'][0]['content'][0]['text'])
                sent.append(payload)
                output={'judgments':[{'turn_id':turn['turn_id'],'key':key,'level':0 if turn['answer'] is None else 2}
                    for turn in payload['turns'] for key in turn['candidate_keys']]}
                response=helper.envelope(output,len(sent))
                response['model']='openai/gpt-6-luna'
                response['id']=fake_key+'-'+str(len(sent))
                response['usage']={'prompt_tokens':100,'completion_tokens':20,'cached_prompt_tokens':0,'cache_write_prompt_tokens':100}
                response['debug']={'api_key':fake_key,'notice':fake_key}
                return httpx.Response(200,json=response)
            with patch.object(run_lab,'LAB_ROOT',root),patch.object(httpx.AsyncHTTPTransport,'handle_async_request',side_effect=AssertionError('real HTTP prohibited')):
                result=asyncio.run(run_lab.execute_approved_plan(output_dir/job['plan_path'],output_dir/job['approval_path'],env,
                    output_dir/job['output_path'],delegate=httpx.MockTransport(respond),campaign_context=context))
            self.assertEqual(result['run_state'],'completed')
            self.assertEqual(len(sent),4)
            self.assertEqual(budget.to_dict()['attempts_started'],4)
            self.assertEqual(Decimal(budget.to_dict()['spent_usd']),Decimal('0.00009'))
            self.assertEqual(len(result['raw_response_artifacts']),4)
            self.assertNotIn(fake_key,json.dumps(result))
            self.assertNotIn(fake_key,json.dumps(events))
            for raw in result['raw_response_artifacts']:
                self.assertNotIn(fake_key,(root/raw['path']).read_text(encoding='utf-8'))
