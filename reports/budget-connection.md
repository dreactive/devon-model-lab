# 금액 예산 보호 연결 검증

2026-11-10 (Asia/Seoul). API를 호출하지 않고 model-lab의 실제 호출 경로에 보호 로직을 연결했다.

- A는 DEVON의 원래 평가 엔진·plan/review를 사용하고, B는 원래 judge_scores를 사용한다. 원래 공통 client의 실제 HTTP 경계에 GuardedTransport를 주입하므로 내부 재시도도 각각 예약/정산한다.
- 단가와 출처·금액/HTTP 시도 상한·정확한 계획에 대한 승인이 없으면 전송 전에 차단한다. 입력·가격·prompt·모델·endpoint·DEVON 소스가 바뀌면 승인도 다시 필요하다. 승인 사용 기록은 독점 생성하며 재사용을 차단한다.
- 사용량 누락·잘못된 모델·미확인 가격·예산 초과·취소·종료 오류에서 추가 전송을 막고 예산/감사 checkpoint를 남긴다. 평가 실패는 기술 실패 종료 코드로 보고한다.
- API 키는 실제 model-lab .env만 읽고 외부 링크·DEVON .env·OS 환경의 키/프록시를 사용하지 않는다. 단가·예산을 채우거나 실제 승인을 만들지 않았다.
- 최종 폴더 전체 테스트: **96개 실행, 95개 통과, 1개 생략**. 생략은 Windows 파일 symlink 권한 부족이다. 외부 .env 경로 차단 코드는 정적 검토했고 일반 외부 경로 거부도 확인했다.
- 기존 A/B dry-run 각각 1건 통과. 현재 실제 설정으로 만든 A/B 계획은 budget_missing/http_attempt_cap_missing/model_price_incomplete 상태다.
- DEVON 추적 파일 **1,265개 지문**, git 상태와 bytecode 디렉터리 목록이 작업 전과 같다. 수정·커밋하지 않았다.
- 실제 API 호출 **0회**. 가상 가격·임시 승인과 메모리 모의 Responses 응답만 사용했다. 실제 공급자 청구를 검증했다는 뜻은 아니며 이미 보낸 요청의 청구를 취소할 수는 없다.

[전체 테스트 로그](../runs/20261110T132722Z-budget-guard/tests.txt), [검증 JSON](../runs/20261110T132722Z-budget-guard/verification.json), [차단된 A 계획](../runs/20261110T132722Z-budget-guard/A-blocked-plan.json), [차단된 B 계획](../runs/20261110T132722Z-budget-guard/B-blocked-plan.json).

승인 실행은 README에 적힌 run_lab.py 경로만 사용한다. DEVON 원래 CLI의 직접 --execute는 수정하지 않았고 USD 보호 대상이 아니다. 별도 의미 Judge와 임의 grader는 새 진입점에 노출하지 않는다. 기존 미검수 사례와 모델 교체 근거 부족 판단은 유지한다.
