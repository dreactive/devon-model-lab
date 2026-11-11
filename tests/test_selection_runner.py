"""Selection reaches the original evaluator, measurements and guarded B route."""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import httpx
import run_lab
from lab_paths import attach_devon
import test_run_lab as fixtures

LAB = Path(__file__).resolve().parents[1]
DEVON = Path('C:/Users/dreac/Desktop/kdt/devon')
attach_devon(DEVON)


class SelectionRunnerTests(unittest.TestCase):
    def test_unlisted_model_cannot_produce_selected_cost_measurement(self):
        import cost_estimate
        args=SimpleNamespace(experiment='A',manifest=LAB/'manifests/baseline.json',
            cases=LAB/'cases/question/benchmark-v1',split='dev',selection_path=LAB/'selections/dev-30pct-v1.json')
        with self.assertRaisesRegex(ValueError,'selection_model_mismatch'):
            cost_estimate.requests(args,DEVON)

    def test_unlisted_model_cannot_run_selected_a_dry(self):
        with self.assertRaisesRegex(ValueError,'selection_model_mismatch'):
            asyncio.run(run_lab.dry_run_question({'cases_path':str(LAB/'cases/question/benchmark-v1'),
                'manifest_path':str(LAB/'manifests/baseline.json'),
                'selection_path':str(LAB/'selections/dev-30pct-v1.json'),'split':'dev'}))

    def test_a_dry_runs_exact_frozen_subset_including_recovery(self):
        from case_selection import resolve_selection
        profile = LAB / 'selections/dev-30pct-v1.json'
        root = LAB / 'cases/question/benchmark-v1'
        selected = resolve_selection(profile, lab_root=LAB, cases_path=root, experiment='A', split='dev')
        result = asyncio.run(run_lab.dry_run_question({'cases_path':str(root),
            'manifest_path':str(LAB / 'manifests/elice-30pct/gpt-6-luna.json'),
            'selection_path':str(profile), 'split':'dev'}))
        self.assertEqual({row['case'] for row in result['cases']}, {f'{key[0]}.v{key[1]}' for key in selected.case_keys})
        self.assertEqual(len(result['cases']), 11)
        self.assertTrue(all(row['status']=='validated_only' for row in result['cases']))
        recovery = [row for row in result['cases'] if row['output'].get('execution_scope')=='recovery_component']
        self.assertEqual(len(recovery), 1)

    def test_cost_measurement_uses_exact_same_selection(self):
        import cost_estimate
        for experiment, corpus, count in [('A','question/benchmark-v1',11),('B','answer/main-v1',4),('B','answer/legacy-na-v1',1)]:
            with self.subTest(corpus=corpus):
                args = SimpleNamespace(experiment=experiment,manifest=LAB/'manifests/elice-30pct/gpt-6-luna.json',
                    cases=LAB/'cases'/corpus,split='dev',selection_path=LAB/'selections/dev-30pct-v1.json')
                _, _, measured = cost_estimate.requests(args,DEVON)
                self.assertEqual(len(measured),count)
                self.assertTrue(all('holdout' not in row['case_id'] for row in measured))

    def test_guarded_b_route_sends_only_the_selected_interview(self):
        from execution_policy import build_plan, plan_digest
        helper = fixtures.RunnerTests()
        with tempfile.TemporaryDirectory(dir=LAB/'tests') as directory:
            root,plan_file,approval,env = helper.prepare(directory,'B',attempts=2)
            selections = root/'selections'
            selections.mkdir()
            profile=selections/'fixture.json'
            profile.write_text(json.dumps({'version':1,'selection_id':'fixture',
                'reference_population':{'A':35,'B':17,'total':52},'split':'dev',
                'model_ids':['gpt-5.6-luna'],'review_status':'unreviewed',
                'datasets':[{'experiment':'B','cases_root':'cases/answer/main-v1',
                    'cases':[{'case_id':'b-main-02','version':1}]}]}),encoding='utf-8')
            plan=build_plan(devon_root=DEVON,lab_root=root,cases_path=root/'cases/answer/main-v1',
                manifest_path=root/'manifests/baseline.json',pricing_path=root/'pricing.yaml',
                experiment='B',split='dev',selection_path=profile,base_url='https://example.invalid/v1',
                budget_usd='10',max_http_attempts=2)
            plan_file.write_text(json.dumps(plan),encoding='utf-8')
            approved=json.loads(approval.read_text())
            approved['plan_sha256']=plan_digest(plan)
            approval.write_text(json.dumps(approved),encoding='utf-8')
            sent=[]
            def respond(request):
                body=json.loads(request.content)
                payload=json.loads(body['input'][0]['content'][0]['text'])
                sent.append(payload)
                judgments=[{'turn_id':turn['turn_id'],'key':key,'level':0 if turn['answer'] is None else 2}
                    for turn in payload['turns'] for key in turn['candidate_keys']]
                return httpx.Response(200,json=helper.envelope({'judgments':judgments}))
            with patch.object(httpx.AsyncHTTPTransport,'handle_async_request',side_effect=AssertionError('real network prohibited')):
                result=helper.execute(run_lab,root,plan_file,approval,env,httpx.MockTransport(respond))
            self.assertEqual([row['case_id'] for row in result['cases']],['b-main-02'])
            self.assertEqual(len(sent),1)
            self.assertEqual(result['cost_budget']['attempts_started'],1)
            self.assertEqual(result['run_state'],'completed')
