# 실험 방법과 재현 경계

대상은 2026-11-11 Elice 프록시를 통해 수행한 DEVON 모델 비교 진단 실험이다. 이 문서는 실제 수행 방법을 설명한다. 정답과 의미 기준의 검수 상태는 모두 `unreviewed`이며, A 의미 Judge는 호출하지 않았다. 모델 품질 순위나 합격 임계값을 검증한 실험으로 해석하지 않는다.

관련 문서: [결과](RESULTS.md), [질문·기대 기준·모델 실제 출력·판정 사례집](CASEBOOK.md), [선택 원문](../reduced-dev-30pct.md), [과거 계획과 실제 차이](../discrepancies.md).

## 1. 실험 질문

- A: 동일한 Director v8 입력에서 질문 생성과 독립 review를 기존 서비스 계약대로 마칠 수 있는가? 생성 질문이 의미상 좋은지는 별도 사람 검수와 교정한 Judge가 필요하다.
- B: 동일한 `report_score` v3 면접 입력에서 턴×평가 key의 0~4 단계 또는 `not_applicable`을 반환하는가? 반환 판정이 미검수 정답 초안과 얼마나 일치하며 원래 서비스의 총점에 어느 정도 차이를 만드는가?
- 공통: strict JSON Schema, 비스트리밍 출력 2,000토큰, 기존 timeout 30초라는 실행 조건에서 어떤 호환성·스키마·서비스 계약 실패가 발생하는가? 실제 HTTP 시도별 사용량과 제공 단가를 연결할 수 있는가?

`report_score`는 평가 단계 판정이다. B에서 면접 보고서 서술 생성이나 `answer_analysis` 품질 비교를 새로 실행하지 않았다. A에 전달하는 분석은 기존 서비스의 canonical `AnswerAnalysis` 입력이며, 새 분석 모델의 출력으로 대체하지 않았다.

## 2. 코퍼스와 선택

전체 합성 초안은 A 35개와 B 17면접, 총 52입력이다. 사용자가 요청한 약 30%를 전체 52입력 기준으로 해석하여 **16/52=30.8%**를 고정했다. 선택은 기존 dev에서만 이루어졌으며, 기존 dev 38입력과 비교하면 42.1%다. **holdout 실행은 0건**이다.

고정 ID와 버전은 [dev-30pct-v1.json](../../selections/dev-30pct-v1.json), 모델 명단·manifest·출처는 [실험 메타데이터](../../experiments/dev-30pct-v1.json)에 있다. 선택 파일의 고정 SHA-256은 `f3dc03a866c9e5d299ff5f6860252ef763ecaeb879d80f1d3f0c22b18aa4bfd5`다. 여섯 모델에 같은 선택을 적용했다.

| 구분 | 선택 | 세부 범위 |
|---|---:|---|
| A | 11개 | 10유형, 5개 프로젝트 묶음; service 10개와 recovery component 1개 |
| B main | 4면접 | 현행 계약의 평가쌍 68개 |
| B legacy | 1면접 | 구형 NA 계약 진단의 평가쌍 30개 |
| B 합계 | 5면접 | 45턴, 98쌍=숫자 단계 85쌍+NA 13쌍; null 답변 2개 |

A는 첫 HR 질문, 충분한 답변 이후 새 목적, 후기 partial, 모름·경험 없음, 기여 범위 정정, 부분 자료, retrieve·skip, JD 연결, 마지막 domain 턴, recovery 관찰의 지시 주입을 포함한다. A control 33개는 기준의 구조·참조를 확인하는 자료이며, 이번에 의미 Judge control 교정에 사용한 호출 수는 0회다.

B main에는 HR null 답변, 답변 안의 지시 주입, 프로젝트 이해 null 답변, 실질 답변과 `tool_error` 관찰을 남겼다. 축소로 기여도 2단계·프로젝트 이해 3단계·문제 해결 0단계·직무 적합성 1단계가 빠졌다. 기술적 근거와 의사소통은 0~4단계가 남지만 원래 단계별 최소 3개 커버리지는 충족하지 않는다. 빠진 단계를 채우기 위해 정답을 수정하지 않았다.

## 3. 모델과 실행 조건

| 모델 ID | 최종 사용 경로 | 동일하게 유지한 출력 조건 |
|---|---|---|
| `gpt-6.1-sol` | native Responses | strict JSON Schema, 출력 상한 2,000 |
| `gpt-6-luna` | native Responses | 동일 |
| `gemini-3.8-flash` | Chat Completions 호환 브리지 | 동일 |
| `gemini-4-argon` | Chat Completions 호환 브리지 | 동일 |
| `claude-haiku-5-5` | Chat Completions 호환 브리지 | 동일 |
| `claude-sonnet-5-5` | 같은 Chat 브리지 요청, 명시적 거절 | schema 완화 없이 중단 |

모델명·제공 단가는 사용자 제공 문서와 고정 설정에서 가져왔다. 이 기록은 다른 계정·시점의 모델 제공 여부나 현재 가격을 보증하지 않는다. [pricing.yaml](../../pricing.yaml)과 실행별 가격 사본·지문을 함께 봐야 한다.

초기에는 제공 문서의 Responses 경로를 사용했다. Gemini가 Responses의 `text` 매개변수를 거절하여, Gemini·Claude 네 모델은 model-lab의 Chat 브리지를 사용했다. 브리지는 원래 프롬프트·payload·같은 strict schema·`store=false`를 전달했다. GPT 두 모델은 Responses 경로를 유지했다. 따라서 **모든 모델의 wire protocol이 같았다고 주장하지 않는다**. 이 경로 차이 자체가 비교 조건이다.

초기 4,096토큰 비스트리밍 요청이 프록시의 2,000토큰 상한으로 거절된 뒤, 후속 성공·평가 요청은 모두 2,000토큰으로 고정했다. 출력 상한에는 제공자 추론 토큰도 포함된다. 기본 추론 설정을 별도로 변경하지 않았고 온도 숫자를 새로 고정하지 않았다. 서비스의 `temperature: null`은 온도 인수를 보내지 않는다는 뜻이다.

## 4. 기존 서비스와 데이터 경계

DEVON은 읽기 전용 외부 의존성으로 참조했다. 별도 vendor 복사본이나 editable 설치를 사용하지 않는다. 실행은 `PYTHONDONTWRITEBYTECODE=1`과 `-B`를 사용하며, model-lab의 adapter가 프로세스 안에서 원래 서비스 호출 계층에 금액 보호 transport를 주입한다.

A는 기존 평가 엔진과 Director plan/review를 사용한다. `a-dev-0020`은 typed `RecoveryFeedback`을 전달하는 component 사례이며 다른 service 사례와 의미가 같다며 합치지 않는다. 입력의 `control`, 기대 기준, 검수 정보는 모델 payload와 분리한다. 사례별 동적 schema를 해당 입력과 연결하고 참조 ID·허용 Persona·부모 턴 등의 계약 검사는 기존 코드에 맡긴다.

B는 원래 report 입력 변환과 `judge_scores`를 사용한다. `turn_no`→문자열 `turn_id`, rubric 조립, candidate key와 턴별 허용 근거 변환을 유지한다. 별도 gold·허용 단계·설명·검수 정보는 모델에게 정답으로 보내지 않는다. 후보 목록에 없는 key를 NA 정답으로 만들어 넣지 않는다. null 답변은 다른 턴이나 프로젝트 자료에서 응답을 만들어 보충하지 않는다.

## 5. 실행 규모·중단·이어쓰기

계획은 16입력×6모델=96개 모델·사례다. 정상 완료에는 모델당 A11×plan/review 2회+B5×1회=27HTTP, 6모델 합계 162HTTP가 필요하다. B 내부 재시도까지 포함한 상한은 모델당 32HTTP, 전체 192HTTP다. **96은 HTTP 호출 수가 아니다.** 별도 smoke·반복·A 의미 Judge는 추가하지 않았다.

실제 전송은 전체 기간을 합쳐 125회다. 초기 실행→continuation-1→recovery-2→recovery-3→recovery-4를 출처별로 연결했다. 완료 결과는 재사용하고 다시 호출하지 않았다. 로컬 `attempt-1` 등이 폴더마다 반복되므로, 물리 시도 ID는 원래 실행 경로와 로컬 ID를 조합해 중복을 제거한다. SDK 결과 행이 없는 전송도 장부에서 남긴다.

원본 사례 행은 79개(정상 56·실패 23)다. Argon의 마지막 A 응답 없는 취소는 원본 결과 행이 없는 별도 `interrupted` 관찰이다. Sonnet의 첫 strict 요청 거절도 `interrupted` 1개로 남고 나머지 15개는 `not_executed`다. 최종 96개 상태는 정상 56·실패 23·중단 2·미실행 15다. 출력 없는 관찰에 SDK 행·가짜 출력·0토큰·0달러를 만들지 않았다.

Argon `a-dev-0025`의 취소에는 30초 timeout 설정이 있었으나, 기록만으로 공급자 오류나 timeout 원인을 확정하지 않았다. 원인 표시는 `request_cancelled`이며 재시도하지 않았다. Sonnet은 `response_format`과 강제 구조화 출력 미지원의 HTTP 400을 명시했으므로 schema를 완화하거나 다른 모델로 대체하지 않았다.

## 6. 평가·분모·지연

A의 기술 정상 처리는 원래 서비스가 schema·계약 검증을 통과했다는 뜻이다. 좋은 질문인지, 맥락에 적절한지의 의미 정확도는 미측정이다. 독립 review는 A 서비스의 정상 단계이며 별도 의미 평가 Judge로 세지 않는다.

B main의 strict 일치는 `(turn_id, key)`의 반환 단계가 미검수 gold 초안과 같은 쌍 수다. acceptable 일치는 별도 허용 집합과 비교하는 진단이며 승인된 정답이 아니다. **main 분모는 모델별 계획 68쌍으로 유지**한다. Haiku main 1면접 실패로 실제 비교는 51쌍이지만 표시값은 `29/68 (실제 비교 51, 미가용 17)`이다. 실패한 17쌍을 분모에서 제거해 좋아 보이게 하지 않는다. Sonnet은 미평가로 표시한다.

단계 MAE는 비교 가능한 숫자 단계 쌍의 절대오차 평균이다. 서비스 총점 MAE는 예측 단계와 초안 단계를 각각 원래 서비스 점수 계산에 넣은 뒤 면접 총점 절대편차를 평균한 값이다. main 4면접 중 Sol·Luna·Flash·Argon은 4개, Haiku는 3개만 계산 가능하다. 따라서 Haiku 총점 MAE는 관측된 3개에 조건부인 값이다. legacy 30쌍과 NA 진단은 main에 합치지 않는다.

성공 A의 지연은 service wall time을 사용한다. 실패 A의 `service_latency_ms=0` 초기값은 측정된 0ms가 아니므로 기록된 SDK 시도 지연 합계로 파생 분석에 반영하고 `latency_source`를 남겼다. B는 기록된 시도 지연 합계다. 응답·SDK 행 없는 취소와 거절에는 지연을 추정하지 않는다. p50/p95에는 측정된 사례 수를 함께 표시한다.

## 7. 비용 계산과 보호

모든 실제 HTTP 시도 직전에 USD를 예약하고 사용량이 있으면 정산한다. A plan/review와 내부 재시도도 같은 전체 $10/192회 보호 한도를 쓴다. 입력·프롬프트·schema·모델·endpoint·단가·코드·선택·금액/시도 상한의 지문을 계획에 고정하고, 계획에 묶인 승인을 사용한다. 누락 사용량이나 비용 미확인 상태는 후속 전송을 잠근다.

계산은 `Decimal`을 사용한다. 사용량 확인분, 제공 단가로 계산한 범위, 미확인 예약 상한, ledger 차감액, 실제 청구액을 구분한다. 캐시 가격·TTL 구분이 불확실하면 범위를 유지하고, 5개 미확인 시도를 0달러로 치환하지 않는다. 추론 토큰은 출력 토큰의 부분집합이므로 출력 비용에 다시 더하지 않는다. 사용자 지시에 따라 청구 내역을 조회하지 않았다.

B main 인터뷰당 비용은 `case-accounting.json`의 해당 모델 `b-main-*` 4개 비용 하한/상한 합계를 4로 나눈 값이다. 실패 면접의 지출도 포함한다. 이 값은 legacy를 포함한 B5 평균, A+B16 평균, 정답 일치당 비용과 다른 분모다. Haiku는 4면접 비용이 있으나 품질 총점은 3면접만 계산 가능한 점에 주의한다.

실행 후 Haiku의 top-level `cache_write_tokens` 별칭을 parser에 추가했다. 원문 측정과 기존 넓은 비용 범위·예산 차감액은 보존하고 과거 요금을 재계산하지 않았다. 당시 runtime과 현재 parser의 차이는 최종 [integrity.json](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/integrity.json)에 있다.

## 8. 오프라인 재현

게시 아카이브의 파일 해시·96개 슬롯·125개 시도·123개 응답·미확인 사용량·비용 노출액은 DEVON이나 API 키 없이 Python 3.12 이상과 표준 라이브러리만으로 재검산할 수 있다. 저장소 루트에서 다음을 실행한다.

```powershell
python -B tools/verify_published_archive.py
```

기존 서비스의 입력 조립까지 확인하려면 접근 권한이 있는 DEVON checkout과 lab 의존성이 별도로 필요하다. 원본 manifest에는 당시 Windows 절대 prompt 경로가 있고 `selection_check.py`도 그 고정 manifest를 사용한다. 따라서 다른 PC에서 `--devon-root`만 바꾸는 방법으로 재현하지 않는다. 아래 도구가 보존된 DEVON 소스·프롬프트 해시를 확인하고, 최종 출력 상한 2,000의 manifest를 새 폴더에 경로만 바꾸어 만든다. DEVON과 원본 manifest는 수정하지 않는다.

```powershell
python -B tools/prepare_portable_manifests.py --devon-root ../devon --output-dir manifests/local-published
```

생성한 manifest를 명시해 Sol A11의 API 없는 준비 계획을 작성한다. `manifests/local-published`와 출력 파일은 아직 없는 새 경로여야 한다. 다시 실행할 때는 새 경로를 사용한다.

```powershell
python -B run_lab.py --prepare --experiment A --devon-root ../devon --cases cases/question/benchmark-v1 --manifest manifests/local-published/gpt-6.1-sol.json --selection selections/dev-30pct-v1.json --base-url https://offline-preparation.invalid/v1 --max-http-attempts 22 --output runs/local-a-prepare.json
```

`--prepare`는 모델을 호출하지 않으며 예시 도메인으로 네트워크 요청을 보내지 않는다. 단가 또는 예산이 빠진 조건은 `blocked_reasons`에 기록하고 새 실행 승인을 만들지 않는다. 이 점검은 모델 응답·토큰·응답 ID·품질 판정을 생성하지 않는다. 도구는 [아카이브 검증기](../../tools/verify_published_archive.py), [게시본용 manifest 생성기](../../tools/prepare_portable_manifests.py)에서 확인할 수 있다.

lab 의존성은 [pyproject.toml](../../pyproject.toml), 당시 버전은 [requirements-offline.txt](../../requirements-offline.txt), 설치 제약은 [offline-environment.json](../offline-environment.json)을 참조한다. 당시 Python 3.13.7의 기존 설치 배포판을 별도 venv로 복사했으며 `uv.lock` 기반 재현성은 확보하지 못했다. 준비 계획 예시는 필요한 lab 의존성이 설치된 환경을 전제로 하며, 같은 텍스트 생성의 재현이나 새 API 실행을 자동 승인하지 않는다.

실제 모델 호출을 다시 하려면 현재 계정의 지원 경로·가격·사용량 계약을 확인하고 새 계획·한도·승인을 준비해야 한다. 과거 승인·checkpoint를 재사용해 중단된 실행을 자동 재개하지 않는다. 이번 게시를 위해 수행한 작업에서는 API·모델·청구 조회를 추가로 호출하지 않았다.

## 9. 원본 근거와 검증 범위

최종 원본: [분석 JSON](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/analysis.json), [96개 사례·125개 시도 연결](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/case-accounting.json), [상세 보고서](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/report.md), [무변경 검증](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/integrity.json).

원본의 절대 로컬 경로는 역사적 출처 정보다. 게시된 복사본에서는 `artifacts/experiments/elice-dev30-20261111/runs/<원래 실행 폴더명>/...`으로 찾는다. 원본 결과·장부·초기 분석은 수정하지 않았으며 현재 해석은 `final-analysis`를 기준으로 한다. 과거 문서의 “실제 호출 0회”, “단가 미설정” 등은 작성 단계의 상태이고 최종 2026-11-11 상태를 덮어쓰지 않는다.

최종 integrity 기록은 DEVON 추적 파일 1,265개·git 상태·bytecode 디렉터리 동일, 보호 코퍼스 파일 167개 변경 0, 기존 산출물 해시 보존을 보고한다. 이는 해당 실행의 기록이며, 사람의 gold 검수·모델 품질 승인·다른 환경에서의 실행 성공을 뜻하지 않는다.
