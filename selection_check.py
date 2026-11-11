"""Capture the same reduced dev cohort for all six models, without provider calls."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path

from case_selection import resolve_selection, filter_cases
from lab_paths import attach_devon
from score_eval import read_json, load_inputs, load_manifest, validate_case

LAB_ROOT = Path(__file__).resolve().parent


async def run(devon_root: Path, output: Path) -> dict:
    devon = attach_devon(devon_root)
    output = output.resolve()
    if output.exists() or output.is_relative_to(devon) or not output.is_relative_to(LAB_ROOT/'runs'):
        raise ValueError('output_rejected')
    from scripts import run_ai_evaluation as engine
    from eval_cases import load_cases
    from question_runtime import catalogue_rows, inspect_recovery, capture_director_request
    from run_lab import dry_run_question
    from corpus_check import validate_question_drafts, validate_isolation
    from execution_policy import build_plan, plan_digest

    profile = LAB_ROOT/'selections/dev-30pct-v1.json'
    experiment = read_json(LAB_ROOT/'experiments/dev-30pct-v1.json')
    roots = [(LAB_ROOT/'cases/question/benchmark-v1','A',22),
             (LAB_ROOT/'cases/answer/main-v1','B',8),
             (LAB_ROOT/'cases/answer/legacy-na-v1','B',2)]
    selected = {str(root):resolve_selection(profile,lab_root=LAB_ROOT,cases_path=root,experiment=kind,split='dev')
                for root,kind,_ in roots}
    a_root=roots[0][0]
    a_cases=filter_cases(load_cases(a_root),selected[str(a_root)])
    b_cases=[(root,case) for root,kind,_ in roots if kind=='B'
             for case in filter_cases(load_inputs(root),selected[str(root)])]
    if len(a_cases)!=11 or len(b_cases)!=5:
        raise ValueError('reduced_count_mismatch')
    expected_versions=sorted(f'{key[0]}.v{key[1]}' for choice in selected.values() for key in choice.case_keys)
    if len(set(expected_versions))!=16:
        raise ValueError('reduced_identity_mismatch')
    isolation=validate_isolation([read_json(a_root/'inputs'/f'{case.case_id}.v{case.version}.json') for case in a_cases]
                                 +[case.envelope for _,case in b_cases])
    a_drafts=validate_question_drafts(a_root,a_cases,catalogue_rows(a_root),expected_controls=33,expected_decisions=2)
    gold_pairs=0
    levels=Counter()
    main_coverage={key:Counter() for key in ('contribution_clarity','project_understanding','technical_reasoning',
                                          'problem_solving','company_job_fit','communication')}
    null_answers=[]
    for root,case in b_cases:
        case_id=case.envelope['case_id']
        for turn in case.envelope['payload']['service_input']['turns']:
            if turn['answer'] is None:
                null_answers.append([case_id,turn['turn_no']])
        gold=read_json(root/'gold'/f'{case_id}.json')
        gold_pairs+=len(gold)
        for row in gold:
            levels[str(row['level'])]+=1
            if root.name=='main-v1' and type(row['level']) is int:
                main_coverage[row['key']][str(row['level'])]+=1
    if gold_pairs!=98 or levels['not_applicable']!=13 or len(null_answers)!=2:
        raise ValueError('reduced_gold_count_mismatch')

    model_rows,plans=[],[]
    roster=selected[str(a_root)].model_ids
    if tuple(row['model_id'] for row in experiment['models'])!=roster or len(roster)!=6:
        raise ValueError('model_roster_mismatch')
    per_model_normal=2*len(a_cases)+len(b_cases)
    per_model_cap=2*(len(a_cases)+len(b_cases))
    http_counts={'per_model_normal':per_model_normal,'per_model_cap':per_model_cap,
        'six_models_normal':per_model_normal*len(roster),'six_models_cap':per_model_cap*len(roster),
        'includes_judge':False,'extra_smoke':0}
    if (experiment['http_counts']!=http_counts or experiment['repeats']!=1
            or experiment['selected_inputs']!=len(expected_versions)
            or experiment['reference_total_inputs']!=52
            or any(cap!=2*len(selected[str(root)].case_keys) for root,_,cap in roots)):
        raise ValueError('experiment_count_mismatch')
    for model in experiment['models']:
        model_id=model['model_id']
        manifest=(LAB_ROOT/model['manifest']).resolve(strict=True)
        if not manifest.is_relative_to(LAB_ROOT/'manifests'):
            raise ValueError('manifest_path_invalid')
        prompts,limits,metadata=engine.load_manifest(manifest)
        if prompts['director'].model!=model_id or prompts['report_score'].model!=model_id:
            raise ValueError('model_manifest_mismatch')
        dry=await dry_run_question({'cases_path':str(a_root),'manifest_path':str(manifest),
            'selection_path':str(profile),'split':'dev'})
        if len(dry['cases'])!=11 or any(row['status']!='validated_only' for row in dry['cases']):
            raise ValueError('selected_a_dry_rejected')
        a_requests=[]
        for case in a_cases:
            recovery=inspect_recovery(a_root,case.case_id,case.version)
            capture=await capture_director_request(case.model_input(),prompts,limits,
                task_limits=metadata.get('task_limits',{}),feedback=None if recovery is None else recovery.feedback)
            a_requests.append({'case_id':case.case_id,'version':case.version,**capture})
        score_prompt,score_limits,_=load_manifest(manifest,devon)
        b_rows=[]
        for root,case in b_cases:
            row=await validate_case(case,root,score_prompt,score_limits)
            if row['status']!='validated_only' or row['annotations']['review_status']!='unreviewed':
                raise ValueError('selected_b_dry_rejected')
            b_rows.append({'corpus':root.name,**row})
        case_versions=sorted([row['case'] for row in dry['cases']]
                             +[f"{row['case_id']}.v{row['version']}" for row in b_rows])
        if case_versions!=expected_versions:
            raise ValueError('model_cohort_mismatch')
        model_rows.append({'model_id':model_id,'case_versions':case_versions,
            'A':{'original_engine':dry,'request_captures':a_requests},'B':{'cases':b_rows},
            'api_calls':0,'provider_attempts':0,'quality_evaluation':'not_run'})
        for root,kind,cap in roots:
            plan=build_plan(devon_root=devon,lab_root=LAB_ROOT,cases_path=root,
                manifest_path=manifest,pricing_path=LAB_ROOT/'pricing.yaml',experiment=kind,
                split='dev',selection_path=profile,max_http_attempts=cap,
                base_url='https://offline-preparation.invalid/v1')
            if set(plan['selected_case_ids'])!={key[0] for key in selected[str(root)].case_keys}:
                raise ValueError('plan_cohort_mismatch')
            if not {'budget_missing','model_price_incomplete'}<=set(plan['blocked_reasons']):
                raise ValueError('unpriced_execution_not_blocked')
            plans.append({'model_id':model_id,'corpus':root.relative_to(LAB_ROOT).as_posix(),
                'approved':False,'plan_sha256':plan_digest(plan),'plan':plan})
    report={'status':'validated_only','selected_inputs':16,'reference_total_inputs':52,
        'selection_fraction':16/52,'dev_population':38,'selection_of_dev_fraction':16/38,
        'model_count':6,'selection_fingerprint':selected[str(a_root)].fingerprint,
        'experiment_fingerprint':{'path':'experiments/dev-30pct-v1.json',
            'sha256':hashlib.sha256((LAB_ROOT/'experiments/dev-30pct-v1.json').read_bytes()).hexdigest()},
        'api_calls':0,'provider_attempts':0,'review_status':'unreviewed','quality_denominator':0,
        'quality_evaluation':'not_run','A_controls':33,'A_draft_checks':a_drafts,'B_turns':45,
        'gold_pairs':gold_pairs,'numeric_gold_pairs':85,'na_gold_pairs':13,
        'null_answers':sorted(null_answers),'isolation':isolation,
        'main_numeric_coverage':{key:dict(counts) for key,counts in main_coverage.items()},
        'main_missing_levels':{key:[level for level in range(5) if not counts[str(level)]]
                              for key,counts in main_coverage.items()},
        'http_counts':http_counts,'models':model_rows,'plans':plans}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--devon-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=asyncio.run(run(args.devon_root,args.output))
        print(json.dumps({key:result[key] for key in ('status','selected_inputs','model_count','gold_pairs','api_calls','review_status')}))
        return 0
    except Exception:
        print(json.dumps({'status':'failed','error':'selection_validation_rejected','api_calls':0}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
