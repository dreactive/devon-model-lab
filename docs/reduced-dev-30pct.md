# 6개 모델 공통 축소 dev 세트

2026-11-11 사용자 요청에 따라 전체52입력(A35+B17)의30%를 약16개로 해석했다. **A11건+B5면접=16/52=30.8%**이며 모두 기존dev에서 선택했다. 기존dev38개와 비교하면42.1%다. holdout은 이번 선택에 포함하지 않는다. 입력/정답/기준/재질문 sidecar 원본을 복사하거나 바꾸지 않고 정확한 ID+version을 참조한다.

고정 목록은 `selections/dev-30pct-v1.json`, 모델별 manifest와 실행 규모는 `experiments/dev-30pct-v1.json`에 있다. 여섯 모델이 같은 선택 파일을 사용한다. 선택 파일·사례/정답·연결 코드가 바뀌면 계획 지문이 바뀌어 기존 승인은 무효다. 제외된 원본의 검증과 전체root 지문도 유지한다.

## 모델

| 제공한 모델명 | 첨부 문서의 model ID |
|---|---|
| GPT-6.1 Sol | gpt-6.1-sol |
| Gemini 3.8 Flash | gemini-3.8-flash |
| Gemini 4 Argon | gemini-4-argon |
| Claude Haiku 5.5 | claude-haiku-5-5 |
| Claude Sonnet 5.5 | claude-sonnet-5-5 |
| GPT-6 Luna | gpt-6-luna |

사용자가 제공한 HTML에서 식별한 값이다. 첨부 원문의 SHA-256을 experiment 메타데이터에 기록했다. 원문에는6개 모두 Responses 경로가 안내되어 있으나 실제 endpoint·지원 매개변수·strict JSON Schema·usage 호환성은 호출로 확인하지 않았다. 특히 원문의 Sonnet 설명은 JSON schema 제약에 제한이 있음을 알리므로 실제 연결 점검에서 확인해야 한다. 지원하지 않는 형식을 조용히 완화해 다른 조건으로 비교하지 않는다. 단가나 계정의 실제 청구 조건을 확인했다고 표시하지 않는다. pricing.yaml·실제 endpoint/key·예산·승인은 채우지 않았다.

## 선택한 A11

| ID(v1) | 유형·의도 |
|---|---|
| a-dev-0001 | A1 첫 HR 질문 |
| a-dev-0007 | A2 충분한 답변 뒤 새 목적 |
| a-dev-0016 | A3 후기 partial의 실제 미충족 조건 |
| a-dev-0013 | A4 모름/경험 없음 |
| a-dev-0021 | A5 기여 범위 정정 |
| a-dev-0022 | A6 부분 자료의 범위 |
| a-dev-0004 | A7 retrieve 결정 |
| a-dev-0014 | A7 skip 결정 |
| a-dev-0018 | A8 JD 연결, T/D 허용 |
| a-dev-0025 | A9 마지막 domain 턴 |
| a-dev-0020 | A10 재질문 관찰의 주입 문구 |

10개 유형 모두 포함하며5개 프로젝트 묶음을 사용한다. service10건과 recovery component1건을 별도로 보고한다. 기준 control33개는 기술 형식/참조 검사 대상이며 유료 Judge를 실행하지 않는다. 이번에는 나머지 재질문2건을 실행하지 않는다.

## 선택한 B5

| ID(v1) | 범위·포함 이유 |
|---|---|
| b-main-02 | 현행, HR null 답변 |
| b-main-05 | 현행, 답변의 지시 주입 |
| b-main-06 | 현행, 프로젝트 이해 null 답변 |
| b-main-08 | 현행, 실질적 답변과 tool_error 관찰 |
| b-legacy-na-01 | 구형 계약 NA 진단 |

45턴·정답98쌍=숫자85+NA13(7턴), null 답변2개다. 구형 진단은 현행 점수 분모에 합치지 않는다. 축소로 현행 기여도2·프로젝트 이해3·문제 해결0·직무 적합성1 단계는 빠진다. 기술적 근거/의사소통은0~4가 모두 남지만 원래 단계별3개 커버리지는 충족하지 않는다. 빠진 단계를 채우기 위해 정답을 바꾸지 않는다. 이 작은 세트로 전체 모델 성능을 확정하지 않는다.

## 실행 규모와 비용

각 모델은 A11×plan/review2회+B5×1회=정상27HTTP, B 내부 재시도를 포함한 상한32HTTP다. 여섯 모델은 정상162HTTP, 상한192HTTP이며 별도 Judge·추가 smoke·추가 반복은 제외한다. 이전 전체52입력×6모델의522회와 비교하면 정상 호출 수는 약69% 줄어든다. 이전 dev전체×6모델378회와 비교하면 약57% 감소한다. 토큰 길이와 모델 단가가 달라 금액도 같은 비율로 감소한다고 보장하지 않는다.

연결 검사는 첫 선택 A/B 입력으로 수행하고 성공 결과를 해당1회 실험 결과로 재사용하는 방침이다. 이 작업에서 추가 smoke API 호출은 하지 않았다. 전체 사용자 금액 상한은 모델/작업별로 나눠 합계가 상한 안에 들게 해야 한다. 현재 각 계획은 별도 CostBudget이므로 모든 모델에 같은 전체 예산을 중복 부여하지 않는다.

모든 정답·기준은 **unreviewed**다. 검수를 생략한 진단 실험이며 결과의 초안 일치를 정답이 검수된 정확도로 표시하지 않는다. 금액/시도 상한·단가·해당 계획 승인이 없으면 실제 실행은 계속 차단된다.

## API 없는 재검증

model-lab에서 매번 새 출력 경로로 실행한다.

```powershell
.\.venv\Scripts\python.exe -B .\selection_check.py `
  --devon-root 'C:\Users\dreac\Desktop\kdt\devon' `
  --output '.\runs\reduced-dev-새ID\selection-dry-run.json'
```

위 명령은 원래 A 평가 엔진과 B scorer의 요청만 로컬에서 캡처한다. 여섯 모델에 동일한16개 입력을 조립해96개의 논리적 요청을 검사하며 provider 요청·토큰·응답 ID·품질 판정을 만들지 않는다. 실제 실행에서는 A review 요청이 추가되므로96을 HTTP 호출 수로 쓰지 않는다.

계획/예상 도구에는 `--selection`과 해당 모델의 manifest를 함께 준다. 예를 들어 아래는 가격·예산이 없어서 차단된 계획만 작성한다.

```powershell
.\.venv\Scripts\python.exe -B .\run_lab.py --prepare --experiment A `
  --devon-root 'C:\Users\dreac\Desktop\kdt\devon' `
  --cases .\cases\question\benchmark-v1 --split dev `
  --selection .\selections\dev-30pct-v1.json `
  --manifest .\manifests\elice-30pct\gpt-6-luna.json `
  --max-http-attempts 22 --base-url 'https://offline-preparation.invalid/v1' `
  --output '.\runs\reduced-dev-새ID\A-plan.json'
```

위 주소는 오프라인 준비용 placeholder이며 실제 Elice endpoint가 아니다. 실제 사용은 모델별 endpoint/계정 조건을 확인한 새로운 계획과 사용자 금액 상한·승인이 필요하다. B 현행root는4입력·상한8HTTP, 구형root는1입력·상한2HTTP로 나눈다.
