# 비용 계산과 실행 한도 경계

`cost_accounting.py`는 저장된 시도와 사용자가 입력한 가격을 계산하는 offline 모듈이다. provider/HTTP client를 import하지 않고 API를 호출하지 않는다. `pricing.yaml`의 실제 단가는 모두 `null`이며 자동 조회·추정·다른 모델 가격 대입을 하지 않는다. 테스트의 `test-model` 가격과 `example.test` 출처는 계산 검증용 가상 값이다.

## 가격 입력

`load_pricing(path)`는 `version: 1`, `currency: USD`, `unit: 1000000`과 `models` 매핑을 읽는다. YAML 소수는 binary float를 거치지 않고 `Decimal`로 읽는다. 반환값의 단가는 `Decimal`이며 이 반환값 자체를 JSON으로 저장하는 인터페이스는 아니다.

각 모델은 다음 필드를 사용한다.

| 필드 | 의미 |
|---|---|
| `input_usd_per_million` | 100만 입력 토큰당 USD |
| `output_usd_per_million` | 100만 출력 토큰당 USD |
| `cached_input_usd_per_million` | cached 입력의 별도 단가, 없으면 `null` |
| `reasoning_output_usd_per_million` | reasoning 출력의 별도 단가, 없으면 `null` |
| `source_url` | 사용자가 확인한 HTTP/HTTPS 가격 출처 |
| `checked_at` | 유효한 ISO 날짜 또는 시간대가 있는 ISO datetime |
| `price_version` | 비어 있지 않은 가격 확인 버전 |

가격을 수집 상태로 쓰려면 출처·확인일·버전이 모두 필요하다. 기본 단가나 이 출처 필드가 누락, `null`, 빈 문자열이면 그 모델만 `not_collected`/`미수집`으로 두고 `missing_fields`에 이유를 남긴다. 다른 완전한 모델 가격 계산은 계속한다. 비어 있지 않은 음수, bool, NaN/Infinity와 잘못된 출처/날짜는 거부한다. 모델 ID는 시도 기록과 정확히 일치해야 한다.

## 사후 집계

`summarize_results(results: list[dict], pricing: dict) -> dict`는 JSON으로 저장 가능한 보고서를 반환한다. USD는 소수 문자열, 미확정 금액은 `null`이다. 실제 계산에는 `Decimal`을 사용한다.

- 모든 `cases[].attempts`와 독립 `judge_audit[].attempts`를 포함한다. 실패·timeout·재시도를 분모에서 버리지 않는다. 사례 밖 Judge control 비용도 Judge 합계에 포함한다.
- 원래 A CLI checkpoint의 `cases[].judge.attempts`와 `diagnostic_judge.attempts`도 복구한다. 최종 감사와 겹치는 nested 시도는 동일 response ID와 전체 계산 metadata가 일치할 때 한 번만 연결한다. 불확실한 중복은 유지하고 미확정으로 표시한다.
- Judge가 설정되었는데 최종 감사가 없거나 실행이 중단되면, 기록되지 않은 control 비용 가능성을 `incomplete_judge_audits`로 표시하고 전체 비용을 미확정으로 둔다.
- 서로 다른 결과 파일 또는 service/Judge 로그에서 같은 provider/model/response ID가 나타나면 전체 비용과 해당 모델 비용을 미확정으로 둔다. 실제 시도를 임의로 제거하지 않으며 `ambiguous_cross_log_duplicates`를 제공한다. 같은 작업 안의 별도 시도를 response ID만으로 제거하지 않는다.
- 어느 시도든 입력/출력 토큰이 `null`, 누락, 음수, bool이면 해당 사례 비용은 `unconfirmed`/`미확인`이다. 확정된 다른 시도의 `known_subtotal_usd`는 보이지만 전체 `total_usd`는 `null`이다.
- 시도가 없는 dry 사례는 `not_executed`/`미실행`, 비용 `null`이다. 유료 실행 비용 0으로 간주하지 않는다. 미확정 사례 수와 시도 수, 누락 단가/사용량 사례 수와 시도 수를 별도로 제공한다.

기본 계산은 `(input_tokens × input_rate + output_tokens × output_rate) / 1000000`이다. canonical `input_tokens`는 cached를 포함하고 `output_tokens`는 reasoning을 포함한다. 별도 카운터가 있으면 각각 canonical에서 차감한 나머지에 기본 단가를 적용한다. subset이 canonical보다 크거나 올바른 정수가 아니면 미확정이다. 별도 단가가 기본 단가와 다른데 해당 subset 카운터가 없으면 할인이나 추가 청구를 추측하지 않는다. 현재 DEVON `AttemptMetadata`에는 이 두 상세 카운터가 없으므로 별도 단가 사용 시 이 한계가 실제 보고서에 나타난다.

재시도는 같은 사례 또는 같은 Judge 작업 안에서 `(provider, model, prompt_version, schema_version)`이 반복되거나 `is_retry: true`인 시도다. `attempt: 2`만으로 판단하지 않는다. Director plan과 review의 schema가 다르면 review를 재시도로 분류하지 않는다.

`waste`는 재시도 비용, 실패 시도 비용, 실패 사례 전체 비용을 구분한다. 최종 실패 사례는 그 사례의 모든 시도를 포함한다. `retry_or_failure_cost_usd`는 이 집합들의 합집합이므로 같은 시도를 두 번 더하지 않는다. 미확정 비용이 비율 분자나 분모에 있으면 비율도 `null`이다. `service_failures`의 분모는 실제 시도가 있는 `executed_cases`이며, 시도 전 입력 실패는 `preflight_failures`로 별도 기록한다.

전체 및 정확한 모델별로 service/Judge 비용, 사례당·인터뷰당 평균, 지연 p50/p95, 실패 건수와 재시도·실패 비용 비율을 제공한다. 평균의 사례 분모는 실제 실행된 사례다. 같은 `interview_id`가 있으면 인터뷰당 평균에 묶고, 없으면 사례 하나를 인터뷰 하나로 센다. Judge overhead는 service 평균과 분리한다. 지연은 실제 시도가 있고 측정값이 있는 사례만 포함하며 dry-run의 0을 제외한다. p50/p95는 정렬값 사이 선형 보간을 사용한다. 한 사례에서 여러 모델을 썼다면 모델별 지연은 그 모델 시도들의 측정 지연 합이며, 전체 사례 지연과 구분해 해석해야 한다.

정답 일치 1건당 비용의 단위도 구분한다.

- A는 `review_status: approved`이고 `quality: accept`인 성공 사례만 확정 정답 사례로 센다.
- B는 approved 사례에 명시된 정수 `metrics.confirmed_correct_items`, 또는 유효한 `metrics.exact_matches`와 `metrics.denominator`만 쓴다. 현재 B dry-run은 이 품질 지표를 생산하지 않는다.
- A와 B는 각각 `cost_per_confirmed_correct_case_usd`, `cost_per_confirmed_correct_item_usd`를 제공한다. 혼합 보고서에서는 서로 다른 단위를 하나로 합치지 않는다. 분모가 0이거나 비용이 미확정이면 값은 `null`이다.
- 서비스 점수 편차는 approved 사례에 명시된 숫자 `metrics.mean_absolute_deviation`의 사례 평균만 표시한다. 값이 없으면 `quality.service_score_deviation`은 `null`이다. 모델 출력이나 gold를 재해석하여 지표를 만들지 않는다. 합격 임계값도 정하지 않는다.

## 실행 전 예상 범위

`estimate_cost(model, *, input_tokens_lower, input_tokens_upper, output_tokens_upper, calls_lower, calls_upper, pricing)`는 계획 검토용 금액 범위를 반환한다. 출력 하한은 0이다. 입력 토큰 휴리스틱의 정확성은 호출자가 설명해야 하며 `billing_guarantee`는 항상 false다.

단가가 없으면 금액을 만들지 않는다. cached/reasoning별 구성이 없지만 별도 단가가 설정되었다면 하한은 미확정이다. 상한은 해당 종류의 기본/별도 단가 중 큰 값을 사용하여 표시하며, 이 계산 근거를 limitations에 기록한다. 예상 금액은 사용자 실행 승인도, transport의 실제 한도 적용도 아니다.

## 시도별 금액 예약과 실제 호출 연결

`CostBudget(amount_usd: Decimal, max_attempts: int, *, approval_id=None, approved=False)`는 양의 USD cap, 양의 정수 시도 수, 그리고 비어 있지 않은 승인 참조 또는 명시적인 `approved=True`를 요구한다. 승인 참조는 호출자가 전달하는 정보이며 모듈이 사용자 승인을 대신 확인하지 않는다.

`reserve(upper_usd: Decimal) -> str`는 실제 HTTP 시도 직전에 알려진 보수적 상한과 한 번의 시도를 동기적·원자적으로 예약한다. `spent + in_flight_reservations + proposed_upper`가 cap을 넘거나 시도 수를 다 쓰면 `BudgetRejected`를 내고 작업을 시작하지 않는다. 동시 예약도 같은 lock으로 검사한다. 재시도는 매번 따로 예약해야 한다.

`settle(reservation_id, actual_usd: Decimal | None)`는 시도 뒤 실제 비용을 정산한다. 실제 금액이 cap 또는 남아 있는 예약까지 포함한 한도를 초과하면 이후 시도를 멈춘다. 토큰이나 가격이 없어 실제 비용을 알 수 없다면 `None`으로 정산하고 이후 시도를 멈춘다. 이미 진행 중인 HTTP 요청이나 이미 발생한 초과 비용을 되돌릴 수는 없다. 이 때문에 사전 상한은 호출자가 확인한 보수적 값이어야 한다.

`to_dict()`는 승인 참조, 시작한 시도 수, 알려진 spend, 예약 금액, 남은 금액, 미확정 시도, halt 사유를 JSON 형태로 제공한다. 미확정 비용 이후 남은 금액은 `null`이다.

`run_guarded_attempt(budget, upper_usd, operation, cost_of_result)`는 한 시도 단위의 주입 가능한 실행 seam이다. 현재 테스트에서는 다음처럼 메모리 함수만 실행한다.

```python
from decimal import Decimal
from cost_accounting import CostBudget, run_guarded_attempt

budget = CostBudget(Decimal("0.10"), 2, approval_id="offline-simulation-only")
result = run_guarded_attempt(
    budget, Decimal("0.04"),
    operation=lambda: {"simulated_cost": Decimal("0.02")},
    cost_of_result=lambda value: value["simulated_cost"],
)
```

이 seam을 원래 `call_model` 전체 바깥에만 감싸면 내부 재시도를 제어할 수 없다. 후속 구현에서 `adapters/guarded_transport.py`를 추가해 원래 HTTP client의 각 실제 시도에 예약·정산을 연결했다. `run_lab.py`는 원래 A 평가 엔진/B scorer와 이 client를 연결하고, `execution_policy.py`의 단가·금액/시도 상한·계획에 묶인 일회성 승인 검증이 끝나야 전송을 허용한다. 원래 DEVON CLI를 직접 실행하는 별도 경로는 USD 보호 대상이 아니다.

원격 응답 대신 모의 HTTP에서 JSON/SSE, 실제 공통 호출 내부 재시도, plan/review 공유, 누락 사용량·알 수 없는 가격·취소·중단·종료 실패를 검증했다. 사용량이 없는 요청을 무료로 취급하지 않고 이후 호출을 막는다. 진행 중인 청구를 취소할 수 있다는 뜻은 아니다. 실제 모델/API 호출은 수행하지 않았다. 상세 사용법은 README의 승인된 실행 경로를 따른다.

## 검증 근거

`tests/test_cost_accounting.py`는 계산값을 손으로 정한 offline unittest다. 구현 전 실패를 확인한 뒤 구현했고, 검토에서 발견한 nested Judge 누락·중복 결과·시도 전 실패 분모·정밀 소수 예약 문제도 각각 실패 regression을 확인한 뒤 수정했다. 현재 이 파일의 32개 테스트는 통과했다. 실제 API 호출, 실제 청구액 검증 또는 실제 paid adapter 연결 검증은 수행하지 않았다.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cost_accounting.py -v
```
