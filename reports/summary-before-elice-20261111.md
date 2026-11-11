# model-lab 검증 현황

2026-11-11 최신 실행 선택은 동일dev16/52입력(30.8%, A11+B5)×6모델이다. API 없이 선택·호출 경로를 검증했으며 원본 코퍼스는 보존했다. [축소dev검증](reduced-dev-30pct.md)을 우선 참고한다. 아래 전체코퍼스/스켈레톤 기록은 당시의 자료다.

현재 단계: A35건/B17면접의 합성 입력과 정답 초안, 재질문3건 연결을 작성했다. 신규52입력은 API 없는 dry-run 대상이며 모두 unreviewed다. 최신 규모·검증·미완료 범위는 [2단계 검증 보고서](stage2-validation.md)에 기록한다. 아래 1단계 smoke/금액 보호 기록은 당시 자료로 보존한다.

금액 보호 연결 후속 작업: `run_lab.py`가 기존 A 평가 엔진/B scorer의 실제 호출 client에 `GuardedTransport`를 주입한다. 모든 HTTP 시도(내부 재시도 포함) 전에 단가·금액/시도 상한·계획에 묶인 일회성 승인을 확인하고 금액을 예약한다. 가격·예산·승인은 채우지 않았으며 실제 API를 호출하지 않았다. 아래 1단계 실행 기록은 당시의 원본으로 보존한다. 후속 검증: 95개 테스트 통과·1개 권한 제한 생략, API 0회·DEVON 지문 동일. [금액 보호 연결 검증](budget-connection.md)에 근거를 기록했다.

기준일: 2026-11-10 (Asia/Seoul). 모델 실행과 품질 비교를 하지 않은 독립 스켈레톤이다. 아래 결과는 최종 model-lab 경로에서 다시 확인했다.

| 실험 | 설정 모델 | 합성 입력 | 입력 검증 | 서비스·모델 실행 | 품질/점수 편차 | 실패율·지연 p50/p95 | 사례/인터뷰당 비용 |
|---|---|---:|---|---|---|---|---|
| A: Director v8 | gpt-5.6-luna (호출 안 함) | 첫 HR 1건 | 최종 경로 dry-run 통과 | 미실행 | 미수집 | 미수집 | 미수집 |
| B: report_score v3 | gpt-5.6-luna (호출 안 함) | 9턴 인터뷰 1건, gold 18쌍 | 최종 경로 dry-run 통과 | 미실행 | 미수집 | 미수집 | 미수집 |

## 기술 검증

- A는 원래 DEVON CLI의 input_contract를 검증했다. 독립 review·service_execution·diagnostic Judge는 미실행으로 남긴다.
- B는 원래 입력 변환, check_input, report/supplemental 검증과 judge_scores의 전체 사전 검사 후 실제 모델 요청을 offline capture했다. 30개 rubric 문구를 원본 AST에서 읽었고, 골드는 요청에 넣거나 가짜 모델 응답으로 사용하지 않았다.
- 현재 범위는 합성 smoke A 1건 + B 1인터뷰이며 review는 모두 unreviewed다. 승인된 품질 분모는 0이고, 자체적으로 approved로 올리지 않았다.
- 동적 Director/v6/score 출력과 로컬 envelope/gold/review의 스키마 사본 8개, 입력/원본 fingerprint와 재생성 도구를 제공한다.
- 가격은 pricing.yaml의 사용자 입력값만 사용한다. 현재 전 모델 단가·출처·확인일·가격표 버전은 비어 있다.
- 비용 계산은 모든 시도·실패·재시도·Judge control을 포함한다. 전체 총액과 알려진 부분합, 미확인 사용량·미수집 단가의 사례 수를 분리한다. 실제 결과가 없으므로 이번 비용 보고 상태는 모델 미실행이다.
- A·B 사전 비용 계획은 각 smoke에 최대2개 HTTP 시도를 표시하지만 **예상 금액은 미수집**이다. 사용자 승인을 받지 않았고 execution_enabled는 false다.
- CostBudget의 예약/정산은 후속 `run_lab.py` 경로에서 실제 HTTP transport에 연결했다. 원래 DEVON CLI의 직접 실행은 여전히 보호 범위 밖이다. 실제 공급자 호출 없이 모의 transport로만 검증했으며 유효한 단가·예산·승인 없이 실행할 수 없다.

## 실행 기록

- 최종 경로: `C:\Users\dreac\Desktop\kdt\model-lab`
- 전체 offline 테스트 **45/45 통과**: [테스트 로그](../runs/20261110T122439Z-stage1/tests.txt)
- A [기존 CLI dry-run](../runs/20261110T122439Z-stage1/question-dry-run.json), B [요청 캡처 dry-run](../runs/20261110T122439Z-stage1/score-dry-run.json) 모두 입력 1건 통과
- [A 예상](../runs/20261110T122439Z-stage1/question-cost-estimate.json), [B 예상](../runs/20261110T122439Z-stage1/score-cost-estimate.json): 최대 시도 각각 2회, 금액 미수집, 실행 비활성
- [사후 비용 JSON](../runs/20261110T122439Z-stage1/costs.json), [비용·품질 표](costs-stage1.md): 모델 미실행 2건, 실제 총액 미수집
- DEVON 추적 파일 **1,265개 지문**, git 상태, bytecode 디렉터리 목록이 시작 전과 동일: [검증 요약](../runs/20261110T122439Z-stage1/verification.json)
- API/모델 호출 **0회**, DEVON 수정·커밋 없음. 원래 존재한 미추적 폴더도 그대로 유지됨
- 독립 venv의 21개 설치 배포판을 네트워크 없이 구성했으며, 기존 receipt가 있는 빈 환경 재생성도 검증함

## 한계와 미완료 범위

사례는 합성 smoke뿐이다. dev 25+holdout 10의 A 코퍼스와 B 10인터뷰는 생성하지 않았고 holdout 모델 실행도 없다. gold는 작성자 초안이고 rubric도 미검수 초안이다. 독립 두 번째 정답과 사람 간 일치도는 없다. 품질·혼동행렬·QWK·점수 편차·반복 안정성·대표 오분류·비용 대비 품질·단일 Judge 편향을 아직 측정할 수 없다. 기존 모델에 맞춰진 prompt일 가능성도 이후 비교의 한계로 남는다.

uv offline 캐시에는 의존성이 없어서 설치된 배포판 파일을 독립 venv로 복사했다. 설치 버전은 requirements-offline.txt에 기록했지만 uv.lock 기반 재현성은 아직 없다. Windows asyncio의 내부 loopback socketpair 때문에 오프라인 검증 프로세스에 제한적인 sandbox 예외를 사용했으며 원격/API 호출은 하지 않았다.

A7 조회 결정, A10 recovery_feedback, 기존 q10만 선택하는 CLI 제약, B의 기여도 단계 커버리지, 온도와 native provider, 시도별 raw 출력 보존 등 미결정은 [불일치 문서](../docs/discrepancies.md)에 기록한다. USD 예산의 실제 호출 연결은 후속 구현으로 완료했고 [비용 규칙](../docs/cost-accounting.md)에 현재 경계를 설명한다.

서비스 모델 교체를 권고할 근거는 **부족하다**. 이번 근거는 입력·스키마·누출 차단·결과 보존·비용 산술·예산 보호 로직에 대한 오프라인 기술 검증뿐이다. 검수된 정답, 실제 모델 출력, Judge 교정, 비용·지연 측정과 독립 holdout 결과가 없으므로 일반적 정확도나 모델 우열을 판단하지 않는다.
