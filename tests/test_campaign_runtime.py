"""Campaign guards use fake credentials and injected local executors only."""
from __future__ import annotations
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, AsyncMock

import test_execution_policy as fixtures
from cost_accounting import CostBudget
from execution_policy import PolicyError, build_plan

LAB=Path(__file__).resolve().parents[1]
DEVON=Path('C:/Users/dreac/Desktop/kdt/devon')


class CampaignPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ExecutionPolicyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.campaign=self.fixture.lab/'campaigns/fixture.json'
        self.fixture.write(self.campaign,{'budget_usd_total':'10.00','fixture':True})

    def test_campaign_fingerprint_is_pinned_and_revalidated(self):
        plan=build_plan(**self.fixture.kwargs,campaign_path=self.campaign)
        self.assertEqual(plan['config']['campaign_path'],str(self.campaign.resolve()))
        self.assertEqual(plan['fingerprints']['campaign_document']['path'],str(self.campaign.resolve()))
        self.fixture.approve(plan)
        self.fixture.validate(plan)
        self.fixture.write(self.campaign,{'budget_usd_total':'11.00','fixture':True})
        with self.assertRaises(PolicyError):
            self.fixture.validate(plan)

    def test_campaign_must_stay_in_lab_campaign_directory(self):
        foreign=self.fixture.lab/'foreign.json'
        self.fixture.write(foreign,{'fixture':True})
        with self.assertRaises(PolicyError):
            build_plan(**self.fixture.kwargs,campaign_path=foreign)


class CampaignContextTests(unittest.TestCase):
    def test_changed_campaign_and_unlisted_plan_are_rejected(self):
        import campaign_runtime as runtime
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            root=Path(directory)
            (root/'campaigns').mkdir()
            campaign=root/'campaigns/test.json'
            campaign.write_text('{}',encoding='utf-8')
            context=runtime.CampaignContext(CostBudget(Decimal('10'),192,approved=True),campaign,
                runtime.file_sha256(campaign),frozenset({'approved'}),lambda event:None)
            policy=SimpleNamespace(plan_sha256='other',lab_root=root,
                plan={'config':{'campaign_path':str(campaign)}})
            with self.assertRaises(ValueError):context.validate(policy)
            campaign.write_text('{"changed":true}',encoding='utf-8')
            policy.plan_sha256='approved'
            with self.assertRaises(ValueError):context.validate(policy)

    def test_bad_aggregate_allocations_are_rejected(self):
        import campaign_runtime as runtime
        source=LAB/'campaigns/dev-30pct-10usd.json'
        config=json.loads(source.read_text(encoding='utf-8'))
        self.assertEqual(runtime.validate_campaign_config(config)['budget_usd_total'],'10.00')
        config['models'][0]['jobs'][0]['budget_usd']='10'
        with self.assertRaisesRegex(ValueError,'campaign_budget_invalid'):
            runtime.validate_campaign_config(config)


class CampaignExecutionTests(unittest.TestCase):
    def prepare(self,directory):
        import campaign_runtime as runtime
        root=Path(directory)/'lab'
        root.mkdir()
        for relative in ('cases','schemas','selections','campaigns','manifests'):
            shutil.copytree(LAB/relative,root/relative)
        (root/'runs').mkdir()
        # These are explicitly fictional secrets and destinations.
        (root/'.env').write_text('OPENAI_API_KEY=FAKE_TEST_CAMPAIGN_KEY_194\nLLM_BASE_URL=https://example.invalid/v1\n',encoding='utf-8')
        destination=root/'runs/campaign'
        bundle=runtime.prepare_campaign(DEVON,root/'campaigns/dev-30pct-10usd.json',destination,lab_root=root)
        text=(destination/'bundle.json').read_text(encoding='utf-8')
        self.assertNotIn('FAKE_TEST_CAMPAIGN_KEY_194',text)
        self.assertNotIn('https://example.invalid/v1',text)
        self.assertEqual(len(bundle['jobs']),18)
        self.assertEqual(sum(Decimal(job['budget_usd']) for job in bundle['jobs']),Decimal('10'))
        return runtime,root,destination/'bundle.json'

    def test_all_jobs_share_one_global_budget_and_cannot_run_twice(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            runtime,root,bundle=self.prepare(directory)
            budgets=[]
            async def execute(plan,approval,env,output,*,campaign_context):
                budgets.append(campaign_context.budget)
                ticket=campaign_context.budget.reserve(Decimal('0.1'))
                campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
                campaign_context.budget.settle(ticket,Decimal('0.01'))
                campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':'0.01','cost_upper_usd':'0.01'})
                result={'run_state':'completed','cases':[]}
                output.parent.mkdir(parents=True,exist_ok=True)
                output.write_text(json.dumps(result),encoding='utf-8')
                return result
            with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
                result=asyncio.run(runtime.execute_campaign(bundle,lab_root=root,execute_plan=execute))
                self.assertEqual(len(budgets),18)
                self.assertTrue(all(budget is budgets[0] for budget in budgets))
                self.assertEqual(result['global_budget']['debited_upper_usd'],'0.18')
                with self.assertRaisesRegex(ValueError,'campaign_already_claimed'):
                    asyncio.run(runtime.execute_campaign(bundle,lab_root=root,execute_plan=execute))
                # Reformatting the campaign and creating a new bundle hash may
                # never create a second ten-dollar allowance for the same scope.
                source=root/'campaigns/dev-30pct-10usd.json'
                source.write_bytes(source.read_bytes()+b'\n')
                clone=json.loads(bundle.read_text(encoding='utf-8'))
                clone['campaign_sha256']=runtime.file_sha256(source)
                clone_path=bundle.parent/'clone.json'
                clone_path.write_text(json.dumps(clone),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'campaign_already_claimed'):
                    asyncio.run(runtime.execute_campaign(clone_path,lab_root=root,execute_plan=execute))

    def test_duplicate_scope_and_plan_paths_are_not_a_valid_bundle(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            runtime,root,bundle=self.prepare(directory)
            original=json.loads(bundle.read_text(encoding='utf-8'))
            for kind in ('scope','plan_path'):
                value=json.loads(json.dumps(original))
                if kind=='scope':
                    value['jobs'][1]['cases_root']=value['jobs'][0]['cases_root']
                    value['jobs'][1]['experiment']=value['jobs'][0]['experiment']
                else:
                    value['jobs'][1]['plan_path']=value['jobs'][0]['plan_path']
                path=bundle.parent/f'bad-{kind}.json'
                path.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'campaign_bundle_scope_changed'):
                    runtime._bundle(path,root)

    def test_unknown_usage_stops_before_any_later_model(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            runtime,root,bundle=self.prepare(directory)
            seen=[]
            async def execute(plan,approval,env,output,*,campaign_context):
                seen.append(plan)
                ticket=campaign_context.budget.reserve(Decimal('0.1'))
                campaign_context.audit_callback({'event':'reserved','attempt_id':ticket})
                campaign_context.budget.settle(ticket,None)
                campaign_context.audit_callback({'event':'settled','attempt_id':ticket,'cost_usd':None})
                return {'run_state':'budget_stopped','cases':[]}
            with patch('run_lab._precheck',new=AsyncMock(return_value=None)):
                result=asyncio.run(runtime.execute_campaign(bundle,lab_root=root,execute_plan=execute))
            self.assertEqual(len(seen),1)
            self.assertEqual(result['run_state'],'budget_stopped')
            self.assertEqual(result['global_budget']['unknown_attempts'],1)
            self.assertEqual(result['pending_jobs'],17)

    def test_precheck_failure_does_not_claim_or_execute(self):
        with tempfile.TemporaryDirectory(dir=LAB/'runs') as directory:
            runtime,root,bundle=self.prepare(directory)
            execute=AsyncMock()
            with patch('run_lab._precheck',new=AsyncMock(side_effect=ValueError('fixture_precheck'))):
                with self.assertRaises(ValueError):
                    asyncio.run(runtime.execute_campaign(bundle,lab_root=root,execute_plan=execute))
            execute.assert_not_called()
            self.assertFalse((root/'runs/.campaign-claims').exists())
