# 요구와 현재 구현의 불일치

2단계 반영(2026-11-10): A35/B17 및 재질문3건 연결은 사용자 승인 후 구현했다. A7의4개 결정론 검사는 분리했고, A3 후기 상태/A8 T·D 허용/A9 quota는 원래 정책으로 재생한다. A10은 model-lab의 typed runtime adapter와 원본 Judge 요청의 offline 투영 검증으로 연결하며 component 분모를 유지한다. B는 현행15+구형NA2로315쌍을 작성했다. 일반 입력/검수 schema와 사례별 동적 schema도 추가했다. 모든 의미 기준·정답은 unreviewed다.

아래 표는 1단계의 기록을 보존한다. 현재 수치와 구현 범위는 [2단계 검증 보고서](../reports/stage2-validation.md)를 기준으로 한다. 유료 Judge 경로·기존q10 선택 실행·raw 시도 출력 보존 등 보고서의 후속 항목은 완료로 바꾸지 않았다. 단가·예산·실제 실행 승인은 여전히 미설정이다.

기준일: 2026-11-10, Asia/Seoul. 이 문서는 요구를 변경하거나 미검수 기준을 승인하지 않는다. 1단계에서는 아래 항목을 우회하여 성공처럼 표시하지 않는다.

| 항목 | 구현 사실 | 1단계 처리 / 다음 결정 |
|---|---|---|
| 실험 B 교체 | 요청 앞부분과 3단계에는 answer_analysis 지표가 남아 있지만 후반은 report_score로 교체한다. | B는 단계 판정 비교로 해석. answer_analysis v6는 A의 분석 입력/스키마 참고로만 유지. |
| A7 retrieve vs ask | run_director는 질문 생성+독립 review 후 ask를 반환한다. 조회 여부는 verification_decision 코드가 정한다. | 조회 결정 검사와 조회 상태를 반영한 질문의 모델 품질을 구분해야 함. 현재 smoke는 첫 HR만 검사. |
| A10 recovery_feedback | runtime은 typed RecoveryFeedback을 받지만 ai_eval_bridge.prepare whitelist와 executor 호출은 이를 지원하지 않는다. prior_analyses도 전달하지 않는다. | DEVON 무수정·기존 CLI 그대로 조건에서는 직접 주입 불가. 실제 입력처럼 꾸민 필드를 추가하지 않음. 연결 확장 허용 범위를 다음에 결정. |
| 기존 q-0001~0010 재사용 | --cases는 경로 1개만 받고 case ID 필터가 없다. 원래 service_regression의 dev는 q10 외 evidence6/flow1/report12도 포함한다. | 이번에는 기존 q를 복사하거나 실행하지 않음. 원본 회귀 전체 별도 실행 또는 기존 선택 기능 확장이 필요. provenance binding을 생략한 링크 투영은 하지 않음. |
| B의 실행기 | 기존 bridge는 report_score task를 받지 않고 report는 score와 narrative 둘을 실행한다. | 승인한 score_eval.py가 service report 입력 변환 후 judge_scores만 호출. stage1은 요청 캡처만 수행. |
| B 커버리지 | 서비스 6tech/2domain/1HR를 유지한 10인터뷰의 기여도 판정은 HR 10개뿐. 5단계×최소3=15개가 필요하다. | 10개 인터뷰를 임의로 늘리지 않음. 최소15인터뷰 또는 서비스 생성 정책과 다른 scorer-contract 사례를 분리할지 추후 결정. 다중 key 판정 수와 턴 수도 구분. |
| not_applicable | 출력해야 할 candidate pair 안에서만 NA를 판정한다. 후보에 없는 key는 출력 대상 자체가 아니다. | 부재 key를 NA 정답으로 세지 않음. 명시 evaluation_keys의 의도와 scope가 모순되지 않도록 NA/구형 계약 사례를 설계해야 함. |
| 고정 temperature | 서비스 CallLimits/ModelRequest와 /responses 요청에 온도 필드가 없다. | YAML null + service_omitted 기록. 숫자 고정/공급자 간 동일 온도를 주장하지 않음. |
| 공급자별 adapter | 기존 transport는 HTTPS Responses 호환 API에 strict JSON Schema를 보낸다. 임의 native API를 지원하지 않는다. | offline adapter와 Responses HTTP 금액 보호를 제공. native adapter/gateway는 미구현이며 실제 공급자의 schema 강제 여부를 API로 확인하지 않음. |
| 원본 출력 | bridge._attempts는 raw_output을 제거하고 SHA만 보관한다. | 이번에는 모델 출력 자체가 없음. 유료 단계의 시도별 원문 보존은 model-lab 기록 연결이 추가로 필요. 기존 결과에서 원문 복구했다고 주장하지 않음. |
| 비용·사용량 | 실행기 비용은 미설정이며 usage가 없을 수 있다. cached/reasoning token별 내역도 없다. | model-lab pricing.yaml·cost_accounting.py·사후 보고/사전 예상 도구 추가. 현재 단가는 null이고 실제 호출도 없다. 별도 단가와 세부 사용량이 없는 비용을 정확한 값으로 주장하지 않음. |
| 금액 예산 상한 | 기존 --max-model-attempts는 HTTP 시도 상한이고 금액 상한이 아니다. | 후속 run_lab.py 경로의 GuardedTransport에서 내부 HTTP 재시도마다 USD 예약/정산을 연결함. 단가·예산·계획에 묶인 승인이 없으면 전송 차단. 기존 DEVON CLI 직접 실행은 보호 대상이 아니며 이미 진행 중인 청구를 취소할 수 있다고 주장하지 않음. |
| Judge v3 선택 | CLI 기본 Judge는 v2이고 model은 settings.llm_default_model에서 온다. manifest prompt 항목으로 모델을 고르지 않는다. | 유료 단계에서 --judge-prompt와 --judge-prompt-version evaluation-judge-v3 둘 다 지정하고 .env의 Judge 모델을 고정해야 함. |
| Judge 교정 | approved control만 교정에 포함된다. 현재 새 사례와 기존 q10은 unreviewed이며 q-0010은 control도 없다. | 교정 통과나 품질 통과율을 만들지 않음. 사람 검수 완료 후 교정을 별도 승인받아 실행해야 함. |
| 예산 | Director는 plan/review 각 1회로 최대2회. B score는 논리 작업별 CallBudget 최대2회. Judge는 control 판정까지 예산을 공유한다. | 단순 사례 수를 호출 수로 표시하지 않음. 현재 실제 모델 호출 0회. |
| holdout 반복 | B의 3회 반복 안정성과 holdout 1회 실행 정책은 시행 단위를 정해야 한다. | 반복 안정성은 우선 dev에서 설계하고 holdout 재사용을 자동 허용하지 않음. |
| 정답 합의 | rubric seed는 미검수 초안. 두 번째 정답은 독립적인 사람 판정이어야 한다. | 골드는 작성자 초안, 독립 두 번째 정답/사람 간 일치도 미수집. 모델로 gold를 만들거나 자체 검수 승인하지 않음. |
| offline 환경 | uv offline 캐시에 의존성 패키지가 없었다. | 기존 설치 배포판을 별도 venv로 복사하고 versions/receipt 기록. uv.lock은 아직 없음. |

## 원본 위치

- ../devon/backend/scripts/ai_eval_bridge.py: prepare, ServiceExecutor, _attempts
- ../devon/backend/scripts/run_ai_evaluation.py: CLI, load_manifest, ModelAttemptBudget, Judge 생성
- ../devon/backend/app/integrations/llm/client.py: _body, CallBudget, call_model
- ../devon/backend/app/features/interview/evaluation_coverage.py: plan_evaluation_targets
- ../devon/ai/src/devon_ai/agents/director/runtime.py: run_director, verification_decision
- ../devon/ai/src/devon_ai/llm_tasks/report_score.py: check_input, _payload, judge_scores
- ../devon/ai/src/devon_ai/contracts.py: score_candidate_keys, validate_score_judgments
- ../devon/ai/evals/source_snapshot.py: binding source 경로 제한

## 아직 수행하지 않은 범위

35개 A 사례, 10개 B 인터뷰 전체 생성, 사용자 단가 입력·검증, 유료 호출 승인/실행, Judge 교정, 정식 채점·혼동행렬·QWK·서비스 점수 편차·반복 안정성·사람 간 일치도·모델 순위는 아직 수행하지 않았다. Responses 실제 호출 경로의 USD 보호 연결은 후속 구현으로 완료했으나 실제 API로 시험하지 않았고 입력 단가·예산·승인은 비어 있다. 모델 미실행 결과를 실제 비용·품질 자료로 바꾸지 않는다.


## 2026-11-11 실제 Elice 호출에서 확인한 차이

- Elice BASE_URL은 /v1이 필요했다. 초기404 기록은 비용 미확인으로 보존했다.
- 비스트리밍 출력은2000토큰을 넘으면 거절됐다. 모든 성공/평가 요청을 동일한2000상한으로 실행했고, 추론 토큰에 따른 잘림을 별도 집계했다.
- Gemini Responses는text매개변수를 거절했다. DEVON을 바꾸지 않고 모델랩의 Chat 브리지에서 동일 프롬프트·payload·strict JSON schema·store=false를 전달했다.
- Sonnet5.5는 실제로response_format을 지원하지 않는다고 거절했다. 스키마를 완화하거나 다른 모델로 대체하지 않았고15건을 미실행으로 남겼다.
- Argon 마지막A는 응답 없이 취소됐다. 원인 단정·사용량 추정·재호출 없이 별도interrupted 관찰로 고정했다.
- 실패A의service_latency_ms=0은 초기값이었다. 최종 파생 분석은 기록된SDK 지연 합계를 사용하고 출처를 표시한다.
- Haiku원문cache_write_tokens는 보존됐으나 실행시 정규화별칭에 빠져 넓은 비용 범위를 사용했다. 실행 후별칭을 보완했으며 과거장부는 재계산하지 않았다.
- 전체청구금액은 미확인이다. 5개미확인시도를0으로 처리하지 않았으며, 모든 예약상한을 포함한 노출액은USD1.674892650이다. 상세근거: reports/summary.md.
