# 축소 dev 세트 검증

2026-11-11. 전체52입력 기준30% 요청을16입력(30.8%, A11+B5)으로 반영했다. 모두dev이며 holdout은0개다. 여섯 모델이 같은 ID+version 목록을 공유한다. 원본52입력과 기준/정답/sidecar는 보존하며 검수 상태는unreviewed다.

A는10개 유형·5개 프로젝트 묶음, service10+recovery1, control33개다. B는현행4+구형NA1면접·45턴·정답98쌍(숫자85+NA13)이고 null2개·주입 답변·실질 답변의 도구 오류를 포함한다. 축소로 현행 기여도2/프로젝트 이해3/문제 해결0/직무 적합성1 단계는 빠지며 단계별 최소3개 조건도 충족하지 않는다. 기존 정답을 바꿔 빈 단계를 채우지 않았다.

| 범위 | 선택 입력 | 정상 HTTP 예상 | 재시도 포함 상한 |
|---|---:|---:|---:|
| 모델1개 | A11+B5=16 | 27 | 32 |
| 동일 입력을 쓰는6모델 | 입력16, 처리96회 | 162 | 192 |

별도 의미 Judge·추가 smoke·추가 반복은 제외한다. 호출 수는 금액이 아니며 실제 단가/토큰에 따라 비용이 달라진다. 이번 작업은 API0회다. 처음 선택한 A/B 결과를 연결 검사와 본1회 결과에 함께 사용해 추가 smoke를 피하는 구성을 기록했다.

`--selection`은 계획·승인 지문·A원본 loader 이후 필터·B scorer·dry-run·비용 측정에 공통 적용된다. 선택 파일/모델/버전 불일치, holdout 포함, 알려지지 않은ID는 거절한다. 제외된 원본 입력/기준의 검증과 전체root 지문도 유지한다. 선택 파일에 없는 baseline모델로 오프라인 비용 예상이나 dry-run을 하는 경우도 거절한다.

첨부 HTML에서 GPT-6.1 Sol, Gemini3.8Flash, Gemini4Argon, ClaudeHaiku5.5, ClaudeSonnet5.5, GPT-6Luna를 확인하고 개별manifest를 작성했다. 이 문서 확인은 실제 계정/API 호환 검증이 아니다. 단가·예산·실제 endpoint/key·승인 양식은 변경하지 않았다. 비용 보호를 해제하지 않고 새 계획은 미설정 가격/예산으로 차단된다.

선정 이유·모델ID·명령·제약은 [설명 문서](../docs/reduced-dev-30pct.md), 기계가 사용하는 고정 목록은 [selection](../selections/dev-30pct-v1.json)에 있다. 원래 전체52입력 검증 결과는 [2단계 보고서](stage2-validation.md)에 보존한다.

## 최종 경로 검증

최종 model-lab 경로에서 확인한 결과다.

- 전체159개 테스트:158통과,1개는 Windows symlink 권한 제약으로 생략. [로그](../runs/reduced-dev-30pct-final/tests.log).
- [선택 dry-run](../runs/reduced-dev-30pct-final/selection-dry-run.json): 여섯 모델 모두 정확히 같은16개ID/version, 원본 A엔진 및 B scorer 조립 통과. A33controls·B98정답 검사, 로컬 요청 캡처96회, API0·provider attempts0·품질 분모0.
- 모델별3개root×6모델=18개 계획은 단가/예산 미설정으로 모두 차단된다. 선택 파일·전체root·정답·코드·prompt 지문과 계획 SHA를 dry-run에 보존한다.
- DEVON 추적파일1,265개·git상태·bytecode 목록이 전후 동일하다. 원본 사례/정답/기준/sidecar 및 pricing.yaml·models.yaml·approval.example.json 합계170개 파일도 해시가 동일하다.
- 검수 상태는 모두unreviewed다. 실제 Elice API/지원 매개변수·JSON Schema 호환성·사용량 보고·금액·모델 성능은 아직 확인하지 않았다.
