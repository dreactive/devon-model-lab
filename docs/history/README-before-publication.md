# DEVON model-lab

현재 실험 범위: 사용자 요청으로 여섯 모델에 동일한 축소dev **16/52입력(30.8%, A11+B5)**을 사용한다. holdout은 제외한다. [고정 목록·규모·명령](docs/reduced-dev-30pct.md), `selections/dev-30pct-v1.json`, `experiments/dev-30pct-v1.json`을 기준으로 실행한다. 전체 코퍼스는 그대로 보존하며 기본 `corpus_check.py`는 기존52입력 점검용이다. 축소 실험은 `selection_check.py`와 `--selection`을 사용한다.

DEVON 면접 LLM을 비교하기 위한 독립 작업 공간이다. 기본 경로는 입력·스키마 검증과 오프라인 실행 계획 작성이다. `run_lab.py`는 금액 보호가 연결된 A/B 호출 경로를 제공하며, 단가·금액/시도 상한·해당 계획에 대한 승인이 없으면 전송 전에 차단한다. **승인된 합성 초안 A 35건/B 17면접을 작성했다. 실제 API 호출·모델 비교·의미 Judge 교정은 수행하지 않았다.**

## 현재 범위

- 실험 A: Director v8 질문 생성. 기존 `backend/scripts/run_ai_evaluation.py` 평가 엔진을 그대로 사용한다. 승인 실행에서는 `run_lab.py`가 원래 `ModelAttemptBudget`에 보호된 HTTP client를 프로세스 내부에서 주입한다. DEVON 파일은 바꾸지 않는다. `run_a_dry.ps1`은 기존 CLI의 dry-run 편의 명령이다.
- 실험 B: **report_score v3의 턴×key 단계 판정**이다. `score_eval.py`는 기존처럼 dry-only다. 승인된 실제 경로는 `run_lab.py --execute`이며 같은 입력 변환·`judge_scores`·공통 호출 계층에 보호된 HTTP client를 연결한다.
- 신규 합성 초안은 A 35건(25 dev/10 holdout), B 17면접·153턴이다. B 현행 15면접과 구형 NA 진단 2면접은 별도 root다. A 재질문 3건은 `question_runtime.py`에서 원본 typed `RecoveryFeedback`으로 연결한다. 별도 smoke A 1건/B 1면접은 본 평가 수에 합산하지 않는다. 모든 기준·정답은 `unreviewed`이며 모델 품질·순위는 아직 측정하지 않았다.
- DEVON 소스·prompt·eval 입력은 읽기만 한다. editable 설치를 하지 않고 `PYTHONPATH`/명시적 import 경로로 원본을 참조한다. `-B`와 `PYTHONDONTWRITEBYTECODE=1`로 DEVON에 bytecode를 쓰지 않는다.

## 폴더

```text
models.yaml                  후보·온도 정책·미승인 예산 자리
pricing.yaml                 사용자 입력 단가·출처 URL·확인일·가격표 버전
adapters/                    dry-only 인터페이스와 실제 HTTP 시도별 금액 보호
run_lab.py                   오프라인 계획 작성 / 승인된 A·B 실행 진입점
execution_policy.py          설정·입력·단가·승인 검증과 일회성 승인 사용 기록
approval.example.json        approved:false인 비활성 승인 양식
manifests/baseline.json       서비스와 같은 prompt/limits, 로컬 model ID
cases/question/inputs/       A의 실제 service_input
cases/question/expectations/ A의 의미 기준·control·검수 정보
cases/answer/inputs/         B의 실제 report service_input
cases/answer/gold/           B의 독립 단계 정답 배열
cases/answer/reviews/        B의 검수 정보
cases/question/benchmark-v1/ 신규 A 35건·control105개·authoring 원장·재질문 sidecar3개
cases/answer/main-v1/        현행 정책 B 15면접·정답255쌍
cases/answer/legacy-na-v1/   구형 계약 B 2면접·정답60쌍 (NA26 포함)
question_runtime.py          원본 Director 재질문 연결·입력/Judge 문맥의 offline capture
corpus_check.py              신규 전체52입력·정답315쌍·A control105개 offline 검증
schemas/                     서비스 출력 스키마·로컬 envelope 스키마·출처
score_eval.py                B의 offline 전용 검증 진입점
cost_estimate.py             입력 크기/시도 상한 기반 예상 비용 (API 없음)
cost_report.py               결과 attempts 기반 사후 비용·품질 병렬 보고
cost_accounting.py           Decimal 계산·시도별 USD 예산 보호 로직
runs/<새 실행 ID>/           결과·checkpoint (덮어쓰기 거부)
reports/summary.md           실제 검증 현황과 근거 수준
docs/discrepancies.md        요구와 현재 구현의 불일치/미결정
```

## PowerShell: 바로 실행

작업 위치는 `C:\Users\dreac\Desktop\kdt\model-lab`, DEVON은 형제 폴더 `..\devon`이다. 다른 위치에서는 `--devon-root`와 `$env:DEVON_ROOT`를 사용한다. API key 없이 동작하며 `.env`를 읽지 않는다.

```powershell
Set-Location 'C:\Users\dreac\Desktop\kdt\model-lab'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:DEVON_ROOT = 'C:\Users\dreac\Desktop\kdt\devon'

# 신규 전체 합성 초안 검증 (새 출력 경로, API 없음)
$taskCorpusRun = 'stage2-' + [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python.exe -B .\corpus_check.py `
  --devon-root $env:DEVON_ROOT --output ".\runs\$taskCorpusRun\corpus-dry-run.json"

# A: 기존 CLI의 실제 입력 계약 검증, 출력 경로 자동 생성
.\run_a_dry.ps1

# B: 매번 새 출력 경로를 사용
$taskRunId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
.\.venv\Scripts\python.exe -B .\score_eval.py `
  --devon-root $env:DEVON_ROOT --cases .\cases\answer `
  --manifest .\manifests\baseline.json --split all --dry-run `
  --output ".\runs\$taskRunId\score-dry-run.json"

# 로컬 경계 검증 (네트워크/모델 호출 없음)
.\.venv\Scripts\python.exe -B -m unittest discover -s .\tests -v
```

A를 직접 실행하려면 다음과 같다. `$taskRunId`는 위와 같이 새로 만든다.

```powershell
.\.venv\Scripts\python.exe -B "$env:DEVON_ROOT\backend\scripts\run_ai_evaluation.py" `
  --cases .\cases\question --manifest .\manifests\baseline.json `
  --split all --dry-run --output ".\runs\$taskRunId\question-dry-run.json"
```

성공은 기술적인 입력 검증 성공일 뿐이다. `service_execution`과 Judge 검사는 dry-run에서 미실행이며 품질 통과로 바꾸지 않는다. holdout을 모델에 실행한 것도 아니다.

## 환경 재생성

정상적인 패키지 설치가 가능한 환경에서는 uv를 사용할 수 있다. DEVON은 의존성으로 설치하지 않는다.

```powershell
uv sync --no-install-project
```

이번에는 다운로드 없이 작업했다. `uv sync --offline`은 로컬 캐시에 `httpx`가 없어 실패했고, 시스템 Python 3.13.7에 이미 설치된 배포판 파일과 전이 의존성만 `.venv`로 복사했다. 가상환경은 system-site-packages를 사용하지 않는다. 설치 버전은 `requirements-offline.txt`, 방식과 한계는 `docs/offline-environment.json`에 남긴다. **uv.lock 기반 재현성은 아직 확보하지 않았다.**

이미 필요한 패키지가 설치된 PC에서 같은 offline 방식을 재현하려면 비어 있는 `.venv`를 대상으로 다음 명령을 쓴다. `packaging`이 시스템 Python에 필요하다. 실행에 사용하는 진입점은 모두 `python.exe`이며 배포판의 console-script 설치는 하지 않는다.

```powershell
python -B .\tools\bootstrap_offline.py
```

## 설정과 스키마

`models.yaml`에 baseline `gpt-5.6-luna`와 비활성 빈 후보를 둔다. 모델 제공 여부·권한·단가는 확인하지 않았다. 가격은 중복 없이 **pricing.yaml만 원본**으로 사용한다. `temperature: null`은 현재 서비스가 해당 인수를 **전송하지 않음**을 뜻하며 온도를 숫자로 고정했다는 뜻이 아니다. Judge는 후보와 다른 계열로 지정해야 하지만 현재 미설정이다.

`manifests/baseline.json`은 원래 runtime manifest의 task/version/limits와 원본 prompt 경로를 보존하고 model ID만 설정한다. limits는 timeout 30초, 출력 4096토큰, 입력 262144바이트, 응답 1048576바이트다. 가격·provider·온도는 서비스 manifest가 허용하지 않으므로 YAML/출처 기록에만 둔다.

후보를 채운 뒤 새 manifest를 생성할 수 있다. 기존 파일은 덮어쓰지 않으므로 기존 baseline이 있는 디렉터리에서는 재생성 명령이 거부된다. 새 실험 복제본에서 생성하거나 기존 파일을 검토 후 직접 관리한다.

```powershell
.\.venv\Scripts\python.exe -B .\tools\build_manifests.py --devon-root $env:DEVON_ROOT
```

동적 출력 스키마는 서비스 함수가 원본이다. 기존 smoke 사본과 별도로 `schemas/generated/question`에 신규35건의 실제 입력에 묶인 Director 스키마·입력 해시·출처를 보관한다. 새 사례에는 해당 사례에 맞춰 다시 생성한다. 근거 ID·부모 턴·허용 Persona·required key의 enum을 고정한 사본을 다른 사례에 그대로 강제하지 않는다. B는 전역 근거 목록을 턴별 허용 근거로 바꾸는 v3 조립도 그대로 따른다.

## 사례·정답 경계

A 입력의 최상위는 `case_id`, `version`, `control`, `payload`; 모델에 들어갈 수 있는 부분은 `payload`뿐이며 그 안은 정확히 `service_task`와 `service_input`이다. 기대값 파일에는 의미 기준만 쓰고 코드가 검사하는 참조·계약·Persona 조건을 중복 채점하지 않는다. A 분석은 wire가 아닌 canonical `AnswerAnalysis` 입력이다.

B는 `service_task: report`의 실제 `turns`/`rubrics` 형식을 보관하지만 **실행하는 task는 report_score 하나**다. 기존 `_build_inputs`가 `turn_no`를 문자열 `turn_id`로 변환하고 30개 rubric 행을 만든다. `score_eval.py`는 report 서술을 생성하지 않는다. 골드 단계는 별도 `gold/{case_id}.json` 배열이고 `acceptable`, 근거 설명과 rubric 인용은 로컬 채점 자료에만 있다. 골드를 모델의 가짜 응답으로 사용하지 않는다.

작성자는 `Codex`, 검수자와 검수일은 `null`이다. 경계 단계의 불확실성은 pending note/허용 단계에 남기고 사람 확인 전 approved로 바꾸지 않는다. 같은 source group의 dev/holdout 혼용을 거부한다.

## 승인된 실행 경로

기존 `score_eval.py`와 `run_a_dry.ps1`은 계속 dry-only다. 실제 호출을 준비하거나 실행할 때는 **`run_lab.py`만 사용한다.** DEVON의 원래 CLI를 직접 `--execute`로 호출하면 model-lab의 USD 보호가 적용되지 않는다. 원래 저장소를 수정하지 않는 조건 때문에 그 별도 진입점 자체를 잠그지는 않는다.

`run_lab.py`의 기본은 오프라인 `--prepare`다. 입력/기대값/정답·manifest·prompt·단가·DEVON 소스·모델·endpoint 지문과 금액/호출 상한을 하나의 계획에 묶는다. 입력 단가나 예산을 대신 채우지 않는다. 아래 명령에는 예산이 없으므로 차단 사유가 있는 계획만 생성되며 API를 호출하지 않는다.

```powershell
.\.venv\Scripts\python.exe -B .\run_lab.py --prepare --experiment A `
  --devon-root $env:DEVON_ROOT --cases .\cases\question --split all `
  --base-url https://api.openai.com/v1 `
  --output ".\runs\$taskRunId\plan.json"
```

실행을 준비할 때는 사용자가 확인한 가격과 `--budget-usd <사용자 지정 금액>`, `--max-http-attempts <서비스·review·재시도를 합한 상한>`을 지정해 새 계획을 만든다. 출력의 예상 범위·총 시도 상한·계획 SHA-256을 검토한 뒤 `approval.example.json`의 복제본에 직접 승인 여부·계획 SHA-256·승인자·시간대가 있는 승인 시각과 만료 시각을 기입한다. 계획 또는 입력/단가가 바뀌면 기존 승인은 무효다. 이 작업에서 승인 파일을 실제 승인 상태로 만들지 않았다.

그 후에만 다음 형태로 호출할 수 있다. 이 명령은 **실제 API를 사용할 수 있으므로 이번 작업에서는 실행하지 않았다.** 모든 조건이 갖춰져도 `--execute`를 명시해야 한다.

```powershell
.\.venv\Scripts\python.exe -B .\run_lab.py --execute `
  --plan ".\runs\$taskRunId\plan.json" --approval .\my-approved-run.json `
  --env-file .\.env --output ".\runs\$taskRunId\result.json"
```

API 키와 실제 endpoint는 model-lab의 실제 `.env` 파일에서만 읽는다. 외부 `.env` 링크와 DEVON `.env`, OS 환경변수의 키/프록시는 사용하지 않는다. 기본 실행에는 별도 의미 Judge/`--grader`를 노출하지 않는다. A는 기존 plan+review, B는 점수 판정만 실행하며 미검수 결과는 진단으로 남긴다. A 반복 실행은 별도 계획으로 나눈다.

다음 단계에서는 사례/정답 사람 검수, Judge 교정에 쓰일 승인된 control, provider 지원·가격·고정 조건을 먼저 정한다. 매 실행 전 서비스 호출·재시도·Judge control 교정을 포함한 총 호출 상한과 예상 비용을 제시하고 사용자 승인을 받아야 한다. 숫자가 없는 단가나 누락 사용량을 0으로 계산하지 않는다. 형식 실패·timeout은 분모에서 제거하지 않는다.

## 비용 확인

`pricing.yaml`에 모델 ID별 USD/1M 입력·출력 단가, 가격 출처 URL, 확인 날짜(`YYYY-MM-DD`), 가격표 버전을 **사용자가 직접** 채운다. 캐시 입력·추론 출력의 별도 단가도 선택적으로 둔다. 이번 작업에서는 가격을 검색하거나 추정해 채우지 않았다.

입력 크기를 서비스 조립 그대로 읽어 사전 예상 범위를 만들 수 있다. 아래 명령은 모델을 부르지 않고 승인도 대신하지 않는다. A는 정상 완료에 plan+review 2회, B는 1회(공통 호출 계층 재시도 포함 최대 2회)를 기본 상한으로 사용한다. 실제 비교에서는 후보 수·반복 수·Judge 교정 시도를 모두 합한 상한을 지정해야 한다.

```powershell
.\.venv\Scripts\python.exe -B .\cost_estimate.py --experiment A `
  --devon-root $env:DEVON_ROOT --cases .\cases\question --split all `
  --max-model-attempts 2 --max-judge-attempts 0 `
  --output ".\runs\$taskRunId\question-cost-estimate.json"

.\.venv\Scripts\python.exe -B .\cost_estimate.py --experiment B `
  --devon-root $env:DEVON_ROOT --cases .\cases\answer --split all `
  --max-model-attempts 2 --output ".\runs\$taskRunId\score-cost-estimate.json"

.\.venv\Scripts\python.exe -B .\cost_report.py `
  --results ".\runs\$taskRunId\question-dry-run.json" ".\runs\$taskRunId\score-dry-run.json" `
  --pricing .\pricing.yaml --output ".\runs\$taskRunId\costs.json" `
  --markdown ".\runs\$taskRunId\costs.md"
```

위 결과 경로는 실제로 저장한 실행 파일 경로에 맞춘다. 예상 금액은 실제 사용량이 아니다.

예상의 문자 수/4 방식은 토크나이저를 사용하지 않은 근사이며 보장된 하한이 아니다. 상한은 요청의 `max_input_bytes`를 보수적인 입력 토큰 허용량으로, 출력은 `max_output_tokens`를 사용한다. 생성 전에는 review 입력 길이를 알 수 없으므로 정밀한 실청구 상한이 아니라 **예상 범위**로만 제시한다. 가격이 비어 있으면 금액도 미수집이다.

사후 비용은 사례별 **모든 attempts**와 별도의 Judge audit 시도로 계산한다. 실패/재시도를 포함하고, 사용량이 하나라도 없으면 사례 비용을 미확인으로 표시한다. 총액과 알려진 부분합을 구분하며 미확인·미수집 사례 수를 함께 남긴다. 캐시/추론 별도 단가가 있는데 세부 사용량이 없으면 정확한 비용으로 단정하지 않는다.

`CostBudget`은 금액과 시도 수 상한을 함께 적용한다. `GuardedTransport`가 **공통 호출 계층의 내부 재시도까지 각 실제 HTTP 시도 직전** 금액을 예약하고, 응답 사용량으로 정산한다. plan·review·재시도가 같은 예산을 쓴다. 불충분한 잔액·금액 초과·응답 모델 변경·미확인 사용량에서는 이후 전송을 중단한다. 승인은 `runs/.approval-claims`에서 독점 생성으로 한 번만 사용된다. 중단을 같은 승인으로 자동 재개하지 않는다. 예약·정산·중단 내역은 결과 파일에 매 시도 checkpoint로 남는다. 이미 진행된 요청의 청구를 되돌릴 수는 없다.

선택적인 캐시/추론 단가가 비어 있어도 기본 가격이 완전하면 계획을 검토할 수 있다. 실제 응답에 0이 아닌 해당 세부 사용량이 나타났는데 가격이 없으면 할인이나 기본 단가를 추측하지 않고 비용 미확인으로 중단한다. 검증은 가상 가격·임시 승인·모의 transport로만 수행했다.

계산 규칙·분모와 한계는 `docs/cost-accounting.md`, 입력 가격의 버전은 결과의 pricing SHA-256에 남는다. 품질은 검수 완료 자료가 있을 때만 정답 일치당 비용의 분모로 사용하고, 합격 임계값은 만들지 않는다.
