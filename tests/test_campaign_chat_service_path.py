"""Original report scorer through the approved strict Chat boundary, offline only."""
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx
import campaign_runtime as runtime
from cost_accounting import CostBudget
import run_lab
import test_campaign_completed_prefix as prefix_fixtures


class CampaignChatServicePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helper=prefix_fixtures.CampaignCompletedPrefixTests
        helper.setUpClass()
        cls.addClassCleanup(helper.doClassCleanups)
        cls.helper=helper()

    def test_original_b_scorer_uses_strict_chat_with_shared_budget_and_redaction(self):
        directory,bundle=self.helper.prepare('actual-service-chat-offline')
        root=self.helper.root
        job=next(row for row in bundle['jobs'] if row['job_id']=='claude-haiku-5-5-2')
        runnable=[row for row in bundle['jobs'] if row['job_id'] in bundle['execution_job_ids']]
        global_budget=CostBudget(Decimal('9.25213505'),162,approval_id='fake-service-chat-only')
        audit=[]
        context=runtime.CampaignContext(global_budget,Path(bundle['campaign_path']),bundle['campaign_sha256'],
            frozenset(row['plan_sha256'] for row in runnable),audit.append,bundle['continuation'])
        sent=[]
        fake_key='FAKE_TEST_CAMPAIGN_KEY_194'

        def respond(request):
            self.assertTrue(str(request.url).endswith('/v1/chat/completions'))
            body=json.loads(request.content)
            self.assertEqual(body['model'],'claude-haiku-5-5')
            self.assertEqual(body['max_completion_tokens'],2000)
            self.assertIs(body['store'],False)
            self.assertIs(body['stream'],False)
            self.assertEqual(body['response_format']['type'],'json_schema')
            self.assertIs(body['response_format']['json_schema']['strict'],True)
            self.assertNotIn('text',body)
            payload=json.loads(body['messages'][1]['content'])
            self.assertNotIn('gold',payload)
            sent.append(body)
            output={'judgments':[{'turn_id':turn['turn_id'],'key':key,
                'level':0 if turn['answer'] is None else 2}
                for turn in payload['turns'] for key in turn['candidate_keys']]}
            return httpx.Response(200,json={
                'id':fake_key+'-'+str(len(sent)),'model':'anthropic/claude-haiku-5-5',
                'choices':[{'index':0,'message':{'role':'assistant',
                    'content':json.dumps(output),'tool_calls':None,'refusal':None},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,
                    'cached_prompt_tokens':0,'cache_write_prompt_tokens':100,'cache_write_short_tokens':100}})

        with patch.object(run_lab,'LAB_ROOT',root),patch.object(httpx.AsyncHTTPTransport,
                'handle_async_request',side_effect=AssertionError('real network prohibited')):
            result=asyncio.run(run_lab.execute_approved_plan(directory/job['plan_path'],
                directory/job['approval_path'],root/'.env',directory/job['output_path'],
                delegate=httpx.MockTransport(respond),campaign_context=context))
        self.assertEqual(result['run_state'],'completed')
        self.assertEqual(len(sent),4)
        self.assertEqual(len(result['cases']),4)
        self.assertTrue(all(row['status']=='succeeded' for row in result['cases']))
        self.assertEqual(global_budget.to_dict()['attempts_started'],4)
        self.assertEqual(Decimal(global_budget.to_dict()['spent_usd']),Decimal('0.00009'))
        for row in result['cases']:
            self.assertEqual(row['attempts'][0]['input_tokens'],100)
            self.assertEqual(row['attempts'][0]['output_tokens'],20)
        self.assertNotIn(fake_key,json.dumps(result))
        self.assertNotIn(fake_key,json.dumps(audit))
        self.assertEqual(len(result['raw_response_artifacts']),4)
        for artifact in result['raw_response_artifacts']:
            text=(root/artifact['path']).read_text(encoding='utf-8')
            self.assertNotIn(fake_key,text)
            raw=json.loads(text)
            self.assertIn('choices',raw)
            self.assertEqual(raw['model'],'anthropic/claude-haiku-5-5')

