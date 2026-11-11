"""Offline diagnostic analysis of an already-executed fixed campaign."""
import sys
sys.dont_write_bytecode=True
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path

LAB=Path('C:/Users/dreac/Desktop/kdt/model-lab').resolve()
sys.path.insert(0,str(LAB))
from lab_paths import attach_devon
attach_devon(LAB.parent/'devon')
from devon_ai import contracts as c
from devon_ai.llm_tasks.report import _build_inputs
from devon_ai.report_scores import compute_scores


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def pct(values,q):
    if not values:return None
    xs=sorted(values);p=(len(xs)-1)*q;i=int(p);j=min(i+1,len(xs)-1)
    return round(xs[i]+(xs[j]-xs[i])*(p-i),2)
def scores(raw,turns):
    checked=c.validate_score_judgments(c.decode_strict(c.ScoreJudgments,raw),turns=turns)
    result=compute_scores(checked)
    return {'keys':dict(result.key_scores),'total':result.total_score}


directory=Path(sys.argv[1]).resolve()
assert directory.is_relative_to(LAB/'runs')
bundle=read(directory/'bundle.json')
ledger=read(directory/'ledger.json')
campaign=read(directory/'campaign-result.json')
models=[]
all_case_rows=[]
for model_id in ['gpt-6.1-sol','gemini-3.8-flash','gemini-4-argon','claude-haiku-5-5','claude-sonnet-5-5','gpt-6-luna']:
    jobs=[job for job in bundle['jobs'] if job['model_id']==model_id]
    model_events=[event for event in ledger['events'] if event.get('event')=='settled' and event.get('model')==model_id]
    unknown=sum(event.get('cost_upper_usd') is None for event in model_events)
    bounded=sum(event.get('cost_status')=='bounded' for event in model_events)
    exact_total=sum((Decimal(event['cost_usd']) for event in model_events if event.get('cost_usd') is not None),Decimal(0))
    lower=sum((Decimal(event['cost_lower_usd']) for event in model_events if event.get('cost_lower_usd') is not None),Decimal(0))
    upper=sum((Decimal(event['cost_upper_usd']) for event in model_events if event.get('cost_upper_usd') is not None),Decimal(0))
    rows=[];latencies=[];compared=matched=accepted=na_mismatches=0;stage_errors=[];service_deviations=[]
    numeric_pairs=Counter();na_pairs=Counter();predicted_totals=[]
    for job in jobs:
        plan=read(directory/job['plan_path'])
        result_path=directory/job['output_path']
        result=read(result_path) if result_path.exists() else {}
        actual={row.get('case_id',row.get('case','').rsplit('.v',1)[0]):row for row in result.get('cases',[])}
        # The original engine and scorer run sequentially. A halt before an output
        # row is checkpointed still has a real transport attempt in the ledger.
        unresolved=[key for key in plan['selected_case_ids'] if key not in actual]
        job_events=[event for event in model_events if event.get('job_id')==job['job_id']]
        in_progress=result.get('in_progress_case')
        if type(in_progress) is dict:in_progress=in_progress.get('case_id')
        if not any(event.get('sent') is True for event in job_events):in_progress=None
        if not in_progress and unresolved and result.get('run_state') in {'budget_stopped','failed','interrupted'} and job_events:
            in_progress=unresolved[0]
        for case_id in plan['selected_case_ids']:
            row=actual.get(case_id)
            state=row.get('status') if row else 'interrupted' if case_id==in_progress else 'not_executed'
            info={'model_id':model_id,'case_id':case_id,'experiment':job['experiment'],'corpus':job['cases_root'],
                'status':state,'identity_from_sequential_checkpoint':row is None and case_id==in_progress}
            if row:
                latency=row.get('service_latency_ms')
                if latency is None:
                    measured=[attempt.get('latency_ms') for attempt in row.get('attempts',[]) if type(attempt.get('latency_ms')) in (int,float)]
                    latency=sum(measured) if measured else None
                if type(latency) in (int,float):latencies.append(latency);info['latency_ms']=latency
            rows.append(info)
            if not row or state!='succeeded' or job['experiment']!='B':continue
            root=LAB/job['cases_root']
            envelope=read(root/'inputs'/f'{case_id}.v1.json')
            gold=read(root/'gold'/f'{case_id}.json')
            expected={(g['turn_id'],g['key']):g for g in gold}
            predictions={(p['turn_id'],p['key']):p['level'] for p in row['output']['judgments']}
            if set(predictions)!=set(expected):raise ValueError('diagnostic_pair_mismatch')
            for key,g in expected.items():
                prediction=predictions[key];target=g['level'];compared+=1
                matched+=prediction==target
                accepted+=prediction in g.get('acceptable',[target])
                if (prediction=='not_applicable')!=(target=='not_applicable'):na_mismatches+=1
                if type(prediction) is int and type(target) is int:
                    stage_errors.append(abs(prediction-target));numeric_pairs[job['cases_root']]+=1
                if target=='not_applicable':na_pairs[job['cases_root']]+=1
            turns,_,_=_build_inputs(envelope['payload']['service_input'])
            actual_scores=scores(row['output'],turns)
            gold_scores=scores({'judgments':[{'turn_id':g['turn_id'],'key':g['key'],'level':g['level']} for g in gold]},turns)
            deviation=abs(actual_scores['total']-gold_scores['total'])
            service_deviations.append(deviation)
            predicted_totals.append({'case_id':case_id,'corpus':job['cases_root'],'predicted':actual_scores,
                'draft_reference':gold_scores,'absolute_total_deviation':deviation})
    statuses=Counter(row['status'] for row in rows)
    executed=sum(statuses[key] for key in ('succeeded','failed','rejected','interrupted'))
    failures=sum(statuses[key] for key in ('failed','rejected','interrupted'))
    missing_input=sum(type(event.get('input_tokens')) is not int for event in model_events)
    missing_output=sum(type(event.get('output_tokens')) is not int for event in model_events)
    input_tokens=sum(event.get('input_tokens',0) for event in model_events if type(event.get('input_tokens')) is int)
    output_tokens=sum(event.get('output_tokens',0) for event in model_events if type(event.get('output_tokens')) is int)
    model={'model_id':model_id,'planned_cases':16,'case_statuses':dict(statuses),'executed_cases':executed,
        'technical_failures':failures,'failure_rate_executed':failures/executed if executed else None,
        'latency_ms':{'p50':pct(latencies,.5),'p95':pct(latencies,.95),'measured_cases':len(latencies)},
        'http_attempts':sum(event.get('sent') is True for event in model_events),'unknown_usage_attempts':unknown,
        'cost_status':'not_executed' if not model_events else 'unconfirmed' if unknown else 'bounded' if bounded else 'confirmed',
        'cost_usd':str(exact_total) if model_events and not unknown and not bounded else None,
        'known_confirmed_subtotal_usd':str(exact_total),'cost_lower_known_usd':str(lower),
        'cost_upper_usd':str(upper) if model_events and not unknown else None,
        'budget_debited_upper_known_usd':str(upper),'bounded_cost_attempts':bounded,
        'tokens':{'input_known_subtotal':input_tokens,'output_known_subtotal':output_tokens,
            'input_total':input_tokens if model_events and not missing_input else None,
            'output_total':output_tokens if model_events and not missing_output else None},
        'B_draft_diagnostic':{'expected_pairs':98,'compared_pairs':compared,'unavailable_pairs':98-compared,
            'strict_matches':matched,'acceptable_matches':accepted,'na_mismatches':na_mismatches,
            'numeric_stage_mae':sum(stage_errors)/len(stage_errors) if stage_errors else None,
            'service_total_absolute_deviation_mean':sum(service_deviations)/len(service_deviations) if service_deviations else None,
            'service_score_interviews':len(service_deviations),'service_scores':predicted_totals},
        'quality_denominator':0,'review_status':'unreviewed','A_semantic_judge':'not_run','cases':rows}
    models.append(model);all_case_rows.extend(rows)
report={'run_state':campaign['run_state'],'run_error':campaign.get('run_error'),'budget_limit_usd':'10.00',
    'global_budget':campaign['global_budget'],'models':models,'planned_model_case_pairs':96,
    'case_statuses':dict(Counter(row['status'] for row in all_case_rows)),
    'exact_cost_total_usd':str(sum(Decimal(m['cost_usd']) for m in models if m['cost_usd'] is not None))
        if all(m['cost_status'] in {'confirmed','not_executed'} for m in models) else None,
    'known_upper_debit_total_usd':str(sum(Decimal(m['budget_debited_upper_known_usd']) for m in models)),
    'unknown_attempts':sum(m['unknown_usage_attempts'] for m in models),'review_status':'unreviewed',
    'quality_evaluation':'diagnostic_only','semantic_judge_calls':0,
    'limitations':['Draft gold is unreviewed; agreement is not approved accuracy.',
        'A semantic quality was not scored by a separate judge.',
        'Failed and unexecuted cases/pairs remain visible; missing usage is not zero cost.',
        'Budget debit is an upper bound based on supplied tariffs, not a confirmed invoice.',
        'B latency is the sum of attempt latencies; A latency is service wall time.',
        'Any interrupted case identity inferred from sequential checkpoints is explicitly marked.']}
with (directory/'analysis.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
lines=['# Elice 6모델 실험 결과','','동일16개dev세트×6모델, 전체예산$10, 검수상태unreviewed.','',
    f"캠페인 상태: **{campaign['run_state']}**. 품질 수치는 미검수 정답 초안 대비 진단이다. A 별도 의미 Judge는 실행하지 않았다.",'',
    '| 모델 | 성공/실패/미실행 | B 초안 일치 / 계획98쌍 | 지연p50/p95(ms) | 비용USD | 입력/출력토큰 |',
    '|---|---|---|---|---|---|']
for m in models:
    st=m['case_statuses'];success=st.get('succeeded',0);failed=m['technical_failures'];pending=st.get('not_executed',0)
    d=m['B_draft_diagnostic'];b=f"{d['strict_matches']}/98 (비교{d['compared_pairs']})" if d['compared_pairs'] else '미평가'
    latency=f"{m['latency_ms']['p50']}/{m['latency_ms']['p95']}" if m['latency_ms']['measured_cases'] else '미측정'
    cost='미실행' if m['cost_status']=='not_executed' else '미확인' if m['cost_status']=='unconfirmed' else '$'+m['cost_usd'] if m['cost_status']=='confirmed' else '$'+m['cost_lower_known_usd']+'~$'+m['cost_upper_usd']
    tokens=f"{m['tokens']['input_total']}/{m['tokens']['output_total']}" if m['tokens']['input_total'] is not None else '미확인' if m['http_attempts'] else '미실행'
    lines.append(f"| {m['model_id']} | {success}/{failed}/{pending} | {b} | {latency} | {cost} | {tokens} |")
lines+=['',f"전체 보수적 예산 차감(확인된 상한 부분합): ${report['known_upper_debit_total_usd']}. 사용량/비용 미확인 시도: {report['unknown_attempts']}건.",'',
    '정확 비용을 확인할 수 없는 경우 0원으로 합산하지 않았다. 캐시 세부량/단가가 모호하면 비용 범위를 표시하고 상한으로 예산을 차감했다. 별도 세금·계정 청구 조정은 확인하지 않았다.','',
    '전체 전송/응답/요금 근거는 ledger.json, 모델별 결과는 results/, 성공 응답 원문(키 마스킹)은 각 *-raw/에 보관한다. 서비스 점수 편차·NA 불일치·단계 오차와 모든 미실행 사례는 analysis.json에 있다.','']
(directory/'report.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'run_state':report['run_state'],'case_statuses':report['case_statuses'],
    'known_upper_debit_usd':report['known_upper_debit_total_usd'],'unknown_attempts':report['unknown_attempts'],
    'models':[{'model_id':m['model_id'],'statuses':m['case_statuses'],'cost_status':m['cost_status'],'http_attempts':m['http_attempts']} for m in models]},ensure_ascii=True))
