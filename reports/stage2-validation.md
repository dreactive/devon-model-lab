# 2단계 합성 사례·정답 초안 검증

사용자가 승인한 A35건/B17면접과 재질문3건 연결을 model-lab에 추가했다. 모든 의미 기준과 정답은 **unreviewed**, 작성자 Codex, 검수자·검수일 null이다. 독립 에이전트의 초안 점검은 사람의 검수나 승인으로 취급하지 않는다. API·유료 Judge·조회 도구 호출은 0회이며 실제 모델 출력은 생성하지 않았다.

## 산출물과 분모

| 자료 | dev / holdout | 규모 | 저장 위치 |
|---|---:|---:|---|
| A 원본 서비스 입력 | 23 / 9 | 32건 | cases/question/benchmark-v1 |
| A 재질문 component | 2 / 1 | 3건 | 같은 root의 runtime_inputs, catalogue scope로 구분 |
| A 합계 | 25 / 10 | 35건, 의미 기준 및 control105개 | inputs / expectations / authoring |
| B 현행 정책 | 12 / 3 | 15면접·135턴·정답255쌍 | cases/answer/main-v1 |
| B 구형 계약 NA 진단 | 1 / 1 | 2면접·18턴·정답60쌍 | cases/answer/legacy-na-v1 |
| B 합계 | 13 / 4 | 17면접·153턴·정답315쌍 | 각 root의 inputs / gold / reviews |

B 정답은 숫자289쌍과 NA26쌍(서로 다른14턴)이다. null 답변은 b-main-02의1턴, b-main-06의2턴 두 개이며 해당 후보 key는0이다. 현행15면접의 기여도·프로젝트 이해·문제 해결·직무 적합성은0~4 단계별3쌍, 기술적 근거는 단계별12쌍을 배치했다. C-only8턴도 단계별3쌍이며 다른 턴의 communication은 실제 문답에 따라 별도로 작성했다. 구형 NA 진단은 현행 점수 분모에 합치지 않는다. 기존 smoke A1/B1과 기존 q회귀도 신규52입력 수에 합산하지 않는다.

## 원본 경로와 dry-run

`run_lab.dry_run_question`이 원래 A `engine.execute`/runner를 그대로 사용한다. model-lab의 `RecoveryExecutor`만 해당 프로세스에서 주입하고 종료 시 복구한다. 일반32건의 실제 실행은 원래 ServiceExecutor로 위임하며, 재질문3건은 원래 `prepare`를 통과한 context에 typed `RecoveryFeedback`을 별도 인수로 전달해 원래 `run_director`를 호출한다. sidecar는 기대 정답이나 reference_texts로 우회하지 않는다.

`corpus_check.py`는 전체35건의 실제 원본 Director 요청과 동적 스키마·입력 크기를 캡처한 후 로컬 sentinel로 멈춘다. 재질문3건은 원본 ModelJudge v3의 요청도 캡처하여 이전 질문·재질문 사유가 원래 문맥 투영/재검증 뒤에도 남는지 확인한다. 이 캡처에는 기준에 대한 판정이 없으며 provider 시도·토큰·응답 ID를 만들지 않는다.

B17건은 원래 report `_build_inputs` → report_score `check_input` → `judge_scores`로 조립된 실제 요청을 캡처한다. 정답은 별도 annotation 계약으로만 검사하며 요청이나 가짜 모델 응답으로 넣지 않는다. numeric rubric 인용은 원본 seed의30개 행을 AST literal로 추출해 대조한다. seed 모듈을 실행하거나 DB를 사용하지 않는다.

A authoring 원장의 과거 계약으로 원래 Controller quota와 evaluation_targets를 재생하고, 현재 질문/분석·근거·부모 턴을 원래 검사기로 확인한다.105개 control은 모두 실제 서비스 출력 JSON이며 동적 스키마·참조·질문/decision 검사를 통과한다. allowed/forbidden/ambiguous라는 의미 판정의 정확성은 아직 검수하지 않았다. A7의4개 결정론 검사 결과는 retrieve/skip/retrieve/retrieve이며 네트워크 조회를 실행한 것은 아니다. source group과 원문 hash의 dev/holdout 분리를 확인한다.

독립 초안 점검에서 a-dev-0016은 이미 설명한 대안 비교를 다시 요구하고, a-dev-0025는 충분히 답한 지연 안내를 다시 묻는 문제가 발견됐다. 전자는 답변에서 해당 비교를 제거해 실제 미충족 조건과 맞추고, 후자는 기존 요청 조회와 신규 환불 요청의 구분이라는 새 목적으로 수정했다. 모두 배포 전 unreviewed 초안 수정이다.

B에서는 다른 단계에서 communication을 자동 유도하던 규칙을 제거하고 각 턴의 표현을 별도로 판정했다. 알아듣기 쉬운 모름/경험 없음 답변은 null이나 무관한 답변과 구별하고, 필수 설명 일부가 빠진 답변의 C4 초안을 낮췄다. payload의 구형 코퍼스/자료 분리 표시는 제거했다. 도구 오류 관찰은 실질적인 답변이 있는 턴에 배치해 오류를 기술 능력의 부정 근거로 쓰지 않는 조건을 강화했다. 계약·답변·실제 source 입력 해시와 catalogue 일치를 추가 검증했다.

연결 코드 점검에서는 입력 요약만 통과하고 executor가 실패한 사례도 차단하도록 precheck를 강화했다. authoring 원문의 자체 해시뿐 아니라 실제 evidence의 경로·내용·repository/git ref까지 대조하며, dry-run 결과에 전체 차단 계획과 소스/정답/코드 지문을 보존한다.

## 비용과 품질을 함께 읽기

| 범위 | 품질·서비스 점수 편차 | 실행 실패율 | 지연 p50 / p95 | 사례/면접당 비용 | 토큰 사용량 |
|---|---|---|---|---|---|
| A32 서비스 | 미측정, 품질 분모0 | 미측정 | 미측정 / 미측정 | 미수집·실행 안 함 | 미측정 |
| A3 재질문 component | 미측정, 별도 분모 | 미측정 | 미측정 / 미측정 | 미수집·실행 안 함 | 미측정 |
| B15 현행 | 미측정, 정답 미검수 | 미측정 | 미측정 / 미측정 | 미수집·실행 안 함 | 미측정 |
| B2 구형 NA | 미측정, 진단 전용 | 미측정 | 미측정 / 미측정 | 미수집·실행 안 함 | 미측정 |

dry-run 기술 검증 성공은 모델 품질 합격이나 정확도100%가 아니다. 합격 임계값은 정하지 않았다. 단가가 비어 있으므로 예상 금액도 **미수집**이다. 실제 호출·토큰을0원 사용 실험 결과로 해석하지 않는다.

실제 호출 경로에서 plan/review/retry는 같은 GuardedTransport와 USD/시도 상한을 공유한다. 재질문3건도 메모리 MockTransport로 그 경로에 도달한 뒤 사용량 미확인으로 이후 전송이 중단됨을 검사했다. 이 가상 가격·가상 승인 테스트는 실제 실행 승인이 아니다. 새 runtime·adapter·schema 코드도 승인 지문에 포함하므로 변경 시 이전 승인은 무효다. 실제 pricing.yaml·예산·승인 양식은 빈 값/approved:false를 유지했다.

## 남은 작업

사람이 전체 질문/정답·인접 단계·NA 범위를 검수해야 한다. 별도 모델의 의미 Judge 교정과 실제 품질·비용 비교는 아직 수행하지 않았다. 보호된 CLI에는 유료 Judge 실행을 노출하지 않으며 이번 연결은 원본 요청을 API 없이 검증하는 helper를 제공한다. 기존 q10의 선택 실행/provenance 확대, dev 반복 안정성 통계·raw 출력 보존·모델 간 비교 보고는 후속 작업이다. 모델 제공 여부/가격이나 provider 지원을 확인했다고 주장하지 않는다.

## 최종 실행 근거

최종 `C:\Users\dreac\Desktop\kdt\model-lab`에서 다음을 확인했다.

- 전체 테스트133개:132통과,1개는 Windows 파일 symlink 권한이 없어 생략. [최종 로그](../runs/stage2-final/tests-final.log). 로그의 failed/rejected JSON 예시는 의도적인 차단 회귀 검사이며 테스트 실패가 아니다.
- [전체 dry-run](../runs/stage2-final/corpus-dry-run-final.json): A35/B17 입력 모두 validated_only, 정답315쌍, control105개, API0회, provider attempts0, 품질 분모0. 전체 차단 계획·소스/기준/정답/코드 지문을 함께 저장했다.
- 원본 요청 크기: A22,160~31,043바이트, B27,150~28,075바이트. A35건 모두 비용 예상 도구의 측정 크기와 원본 캡처 크기가 일치했고, 재질문 피드백3건을 포함한다. 전부 입력 상한262,144바이트 안이다.
- 비용 예상 자료: [A](../runs/stage2-final/estimate-A.json), [B현행](../runs/stage2-final/estimate-B-main.json), [B구형](../runs/stage2-final/estimate-B-legacy.json). 예시 시도 상한70/30/4는 승인된 금액 예산이 아니다. 세 자료 모두 예상 금액null·not_collected·approved:false·execution_enabled:false다.
- DEVON 전후 지문은 추적파일1,265개, git 상태, bytecode 디렉터리 목록까지 완전히 같다. 기존 untracked 항목도 보존했다. 커밋이나 DEVON 쓰기는 하지 않았다.

전체 파일을 살펴볼 때는 [52입력 사례 목록](../docs/stage2-case-index.md)을 사용한다. 기술 준비는 완료했지만 의미 정답 검수와 실제 모델 성능 비교는 아직 남아 있다.
