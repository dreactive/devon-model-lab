# 동결 개발 입력 16건 사례집

실험 A의 질문 생성 입력 11건과 실험 B의 9턴 문답 입력 5건을, 기대 기준·실제 생성·기술 판정까지 연결합니다. 입력은 합성 데이터이며 기대 기준과 gold는 **unreviewed**입니다. 승인된 의미 정확도 분모는 **0**입니다.

[질문과 기대 기준만 먼저 읽기](QUESTIONS_AND_EXPECTATIONS.md) · [동결 선택 목록](../../selections/dev-30pct-v1.json) · [최종 분석](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/analysis.json) · [사례 회계 원본](../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/case-accounting.json)

## 전체 커버리지

96개 모델·입력 조합은 **성공 56 / 실패 23 / 중단 2 / 미실행 15**입니다. 125개 물리 요청을 출처 폴더로 한정한 ID로 구분했습니다. 원본 응답 파일 123개가 있고, 원래 404와 Argon 취소 요청은 응답 파일이 없습니다. 비용 미확정 5건 중 3건은 HTTP 오류 본문만 존재하며 생성된 모델 답변이 아닙니다. Sonnet의 나머지 15개 사례에는 요청·응답이 없습니다.

| 입력 ID | 구분 / 분류 | 입력 주제·평가 범위 | 성공 | 실패 | 중단 | 미실행 |
|---|---|---|---:|---:|---:|---:|
| [a-dev-0001.v1](cases/a-dev-0001.md) | A / A1 / service | 역할 자료가 없으므로 지원자가 경험을 골라 본인 담당 범위와 협업 경계를 소개할 기회를 준다. | 4 | 1 | 1 | 0 |
| [a-dev-0004.v1](cases/a-dev-0004.md) | A / A7 / service | 중복 방지는 아직 조회로 확인되지 않았다는 범위를 지키면서 중복 요청 처리 방식의 선택 이유를 확인한다. | 4 | 1 | 0 | 1 |
| [a-dev-0007.v1](cases/a-dev-0007.md) | A / A2 / service | 최신 수량 재검증과 제한 재시도 설명은 수용하고 높은 충돌률에서 대안의 선택 기준을 묻는다. | 2 | 3 | 0 | 1 |
| [a-dev-0013.v1](cases/a-dev-0013.md) | A / A4 / service | 잠금 구현을 모른다는 진술을 받아들이고 실제 화면 상태 갱신 범위의 선택 이유를 묻는다. | 4 | 1 | 0 | 1 |
| [a-dev-0014.v1](cases/a-dev-0014.md) | A / A7 / service | 제공된 registry 원문이 확인하는 단일 인스턴스 중복 키 검사 범위 안에서 선택 이유를 묻는다. | 3 | 2 | 0 | 1 |
| [a-dev-0016.v1](cases/a-dev-0016.md) | A / A3 / service | 이벤트 ID 선택 이유는 인정하고 원래 빠진 중복 구분 대안의 비교 조건만 보완한다. | 2 | 3 | 0 | 1 |
| [a-dev-0018.v1](cases/a-dev-0018.md) | A / A8 / service | D의 데이터 수명 관리 경험 연결 또는 T의 관련 저장·삭제 진단을 모두 허용하되 실제로 확인된 경험 범위를 유지한다. | 3 | 2 | 0 | 1 |
| [a-dev-0020.v1](cases/a-dev-0020.md) | A / A10 / recovery_component | 지시가 섞인 피드백을 자료나 권위로 삼지 않고 실제 이벤트 ID 기반 중복 구분의 선택 이유를 묻는다. | 4 | 1 | 0 | 1 |
| [a-dev-0021.v1](cases/a-dev-0021.md) | A / A5 / service | 세금은 동료이고 환불 상태는 본인이라는 정정을 범위대로 반영해 가정형 상태 진단을 묻는다. | 2 | 3 | 0 | 1 |
| [a-dev-0022.v1](cases/a-dev-0022.md) | A / A6 / service | 연결 생성·반환 발췌로는 전체 rollback을 판단할 수 없음을 밝히고 주장한 처리 단위와 선택 조건을 확인한다. | 2 | 3 | 0 | 1 |
| [a-dev-0025.v1](cases/a-dev-0025.md) | A / A9 / service | 이미 설명한 지연 안내를 반복하지 않고 진행 중인 요청의 상태 조회와 새 환불 신청의 의미 차이를 사용자 예로 설명하게 한다. | 2 | 2 | 1 | 1 |
| [b-main-02.v1](cases/b-main-02.md) | B / main | 비동기 알림 · 9턴 · 17개 draft 쌍 | 5 | 0 | 0 | 1 |
| [b-main-05.v1](cases/b-main-05.md) | B / main | 접근제어 gateway · 9턴 · 17개 draft 쌍 | 5 | 0 | 0 | 1 |
| [b-main-06.v1](cases/b-main-06.md) | B / main | 작업 scheduler · 9턴 · 17개 draft 쌍 | 4 | 1 | 0 | 1 |
| [b-main-08.v1](cases/b-main-08.md) | B / main | 배포 rollback · 9턴 · 17개 draft 쌍 | 5 | 0 | 0 | 1 |
| [b-legacy-na-01.v1](cases/b-legacy-na-01.md) | B / legacy NA | 센서 관측 portal · 9턴 · 30개 draft 쌍 | 5 | 0 | 0 | 1 |


## 후보 슬롯별 기술 커버리지

| 후보 슬롯 | 성공 | 실패 | 중단 | 미실행 | 물리 요청 |
|---|---:|---:|---:|---:|---:|
| `gpt-6.1-sol` | 16 | 0 | 0 | 0 | 29 |
| `gemini-3.8-flash` | 8 | 8 | 0 | 0 | 20 |
| `gemini-4-argon` | 15 | 0 | 1 | 0 | 26 |
| `claude-haiku-5-5` | 6 | 10 | 0 | 0 | 22 |
| `claude-sonnet-5-5` | 0 | 0 | 1 | 15 | 1 |
| `gpt-6-luna` | 11 | 5 | 0 | 0 | 27 |


## 읽는 방법과 분리한 정보

- **실제 입력:** 각 페이지의 문답·근거와 동결 입력 JSON입니다. A10의 복구 관찰 sidecar도 표시합니다. 기대 기준/gold는 이 입력에 삽입하지 않았습니다.

- **기대 출력:** A는 allowed/forbidden와 합성 grader_controls이고, B는 (turn_id, key, level) 초안 annotation 및 rationale입니다. A 통제 예시는 업무 정답 문장이 아닙니다.

- **실제 응답:** 최종 서비스 output과 모든 물리 요청의 공개 생성 문자열을 둘 다 보존합니다. A plan/review를 각각 보여 주며 실패·잘림·원본 HTTP 오류도 연결합니다. 공개 생성 텍스트/거부 필드는 완전하게 옮기고 암호화된 reasoning·서명은 원본 링크에만 남겼습니다.

- **기술 판정:** 원래 SDK의 상태·입력 결합·오류 단계와 raw finish_reason/status/잘림 표식을 표시합니다. HTTP 200이더라도 계약·형식 검증에서 실패할 수 있습니다. 의미 실패율로 바꾸지 않습니다.

- **B 초안 비교:** gold와 최종 유효 judgments의 쌍별 값, strict/acceptable 일치 수, 숫자 단계 MAE, 원본 코드 환산 진단을 표시합니다. main과 legacy NA의 분모를 섞지 않습니다.

- **기록이 없는 경우:** 비용 미확정, 응답 누락, 요청 취소, 미실행을 구분합니다. 없는 답변이나 거부를 만들지 않습니다.


실행 후반의 공통 출력 제한은 2,000토큰이며 provider reasoning도 이 제한을 사용합니다. GPT 계열은 Responses, Gemini/Claude는 Chat Completions 호환 브리지를 사용한 조건 차이가 있습니다. 따라서 잘림·strict schema 거절·서비스 성공은 이번 프록시/제한 조건의 기술 관찰입니다.
