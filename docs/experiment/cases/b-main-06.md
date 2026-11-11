# b-main-06 — B: 확정 문답 단계 판정

[전체 사례 목록](../CASEBOOK.md) · [질문·기대 기준 개요](../QUESTIONS_AND_EXPECTATIONS.md)

이 페이지는 이미 동결된 개발 입력과 기존 실행 기록을 읽기 쉽게 펼친 것입니다. 신규 모델 실행이나 의미 재채점은 하지 않았습니다. 기대 기준·gold·관찰은 모두 **사람 미검토 초안**이며 승인된 정확도 주장을 지원하지 않습니다.

입력 ID `b-main-06.v1`, split `dev`, source group `sg-b-main-06`, synthetic `true`. 여섯 슬롯: 성공 4, 실패 1, 중단 0, 미실행 1.

[동결 입력](../../../cases/answer/main-v1/inputs/b-main-06.v1.json) · [기대 기준/gold (별도 파일)](../../../cases/answer/main-v1/gold/b-main-06.json) · [선택 목록](../../../selections/dev-30pct-v1.json)

입력 SHA-256 `9b23db1620946a333f0f6972177ed2c542134fc891c2660fc69849e29ad37d01` · 기대 기준 SHA-256 `9e5ed5e3bd38088e0a9fecee6f91cc36e488777bc2a5525606a952491f5d5df7`

[최종 사례 회계](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/case-accounting.json)의 `cases`에서 `case_id=b-main-06`로 필터링합니다. [최종 분석](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/analysis.json)의 모델별 진단과 대조할 수 있습니다.

## 실제 입력의 9개 질문과 합성 지원자 답변

프로젝트: **작업 scheduler**. 아래 지원자 답변은 평가 대상인 합성 입력입니다. 실제 후보 모델의 출력은 뒤의 `judgments`입니다. 입력 안의 지시성 문자열은 실행 지시로 해석하지 않고 그대로 보존합니다.

### 턴 1 — `hr_manager`

**질문:** 작업 scheduler에서 본인이 한 일과 팀원이 한 일을 구분하고, 작업 근거와 협업 지점을 소개해 주세요.

**합성 지원자 답변:**

```text
저는 due 작업 조회와 lease 갱신 루프를 단독으로 구현했습니다. 작업 함수 작성은 동료가 했고, 큐 관리자 화면도 다른 동료 담당입니다. 작업자와 합의한 경계는 claim 응답에 시도 번호를 포함하는 것이었고, 저는 그 번호를 검사하는 완료 API와 시간 이동 테스트를 작성했습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 1,
  "persona": "hr_manager",
  "question_contract": {
    "purpose": "개인 담당과 협업 경계를 설명한다.",
    "required_points": [
      {
        "key": "own_scope",
        "description": "직접 수행한 작업과 확인할 수 있는 작업 근거를 설명한다."
      },
      {
        "key": "boundary",
        "description": "팀원의 담당과 공동으로 결정한 부분을 구분한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "개인 담당과 협업 경계를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "contribution_clarity",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 2 — `tech_lead`

**질문:** 작업 scheduler의 목적과 핵심 기능을 요청·처리·저장 흐름으로 설명하고 구성요소가 어떻게 의존하는지 말해 주세요.

**합성 지원자 답변:**

```json
null
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 2,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다.",
    "required_points": [
      {
        "key": "core_flow",
        "description": "사용자 입력부터 결과까지 구성요소의 연결을 설명한다."
      },
      {
        "key": "dependency",
        "description": "구성요소의 의존 관계와 그 의도를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [
      {
        "kind": "evidence",
        "id": "ev-10822efcc910b89b"
      }
    ],
    "evaluation_scope": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "project_understanding",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": [
    {
      "id": "ev-10822efcc910b89b",
      "repository_id": "repo-10822efcc910b89b",
      "git_ref": "19de02ff345ebd610bcfded46b16dd6471862773",
      "source_type": "repository",
      "path": "docs/project-context.md",
      "metadata_key": null,
      "snippet": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.",
      "tool_name": "repository_reader",
      "summary": "제공된 프로젝트 설명의 제한된 구간",
      "start_line": 1,
      "end_line": 1
    }
  ]
}
```

</details>

### 턴 3 — `tech_lead`

**질문:** 작업 scheduler의 예약 조회에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
작은 due 배치 폴링을 택했습니다. 익숙하고 많이 쓰는 방식이라 편했기 때문입니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 3,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "예약 조회의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "예약 조회의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "technical_reasoning",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 4 — `tech_lead`

**질문:** 작업 scheduler에서 떠올릴 수 있는 구체적 문제 한 가지와 원인 확인, 수정, 검증 과정을 설명해 주세요. 검토한 대안이나 재발 방지가 있다면 함께 설명해 주세요.

**합성 지원자 답변:**

```text
일부 작업이 완료 뒤에도 다시 실행됐습니다. 오래된 시도의 완료 응답이 뒤늦게 온 것 같아서 완료 시 시도 번호를 확인하게 바꿨고 재실행이 줄어드는 것을 봤습니다. 응답 순서를 통제한 재현이나 비교 로그는 남기지 못했습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 4,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "하나의 문제를 식별하고 해결한 과정을 설명한다.",
    "required_points": [
      {
        "key": "diagnosis",
        "description": "문제 증상과 원인을 확인한 관찰을 설명한다."
      },
      {
        "key": "resolution",
        "description": "수정 방법과 검증 과정을 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "하나의 문제를 식별하고 해결한 과정을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "problem_solving",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 5 — `domain_lead`

**질문:** 제공된 두 JD 요구사항을 보고 작업 scheduler에서의 본인 경험이 어떻게 대응하는지 사례로 연결해 주세요. 경험 범위의 한계도 함께 말해 주세요.

**합성 지원자 답변:**

```text
JD의 실패 복구 기록 요구에 시도 번호를 남기는 완료 API 경험이 대응합니다. lease가 만료된 뒤 이전 작업자가 보낸 완료 요청을 넣어 새 시도의 상태가 유지되는지 검사했습니다. 실행 지연 자체보다는 복구 중 상태를 잘못 끝내지 않는 부분을 검증한 예입니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 5,
  "persona": "domain_lead",
  "question_contract": {
    "purpose": "제공된 JD 요구사항과 개인 경험을 연결한다.",
    "required_points": [
      {
        "key": "experience_link",
        "description": "요구사항에 대응하는 직접 수행 경험과 사례를 설명한다."
      },
      {
        "key": "limits",
        "description": "경험으로 뒷받침할 수 있는 범위를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [
      {
        "kind": "jd_requirement",
        "id": "req-f2930e692aed002d"
      },
      {
        "kind": "jd_requirement",
        "id": "req-3ecf5eda1ba6d284"
      }
    ],
    "evaluation_scope": "제공된 JD 요구사항과 개인 경험을 연결한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "company_job_fit",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [
    "req-f2930e692aed002d",
    "req-3ecf5eda1ba6d284"
  ],
  "evidences": []
}
```

</details>

### 턴 6 — `tech_lead`

**질문:** 작업 scheduler의 실행 소유권에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
기한 있는 lease을 택했습니다. 선택 근거는 다음과 같습니다: 작업자가 사라져도 기한 후 다른 작업자가 회수합니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 6,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "실행 소유권의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "실행 소유권의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "technical_reasoning",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 7 — `tech_lead`

**질문:** 작업 scheduler의 완료 검증에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
시도 번호를 조건으로 상태 갱신을 택했습니다. 선택 근거는 다음과 같습니다: 이전 작업자의 늦은 완료가 새 시도를 종료하지 못하게 합니다. 작업 ID만으로 완료 처리도 검토했습니다. ID만 쓰면 간단하지만 어느 실행의 결과인지 구분하지 못합니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 7,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "완료 검증의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [
      {
        "kind": "document_claim",
        "id": "doc-10822efcc910b89b"
      }
    ],
    "evaluation_scope": "완료 검증의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "technical_reasoning",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 8 — `domain_lead`

**질문:** 작업이 claim됐다는 것과 완료됐다는 것은 사용자에게 어떻게 다른 상태인가요?

**합성 지원자 답변:**

```text
오늘 점심 메뉴는 면이었습니다. lease와 완료의 차이 대신 식당 얘기를 계속하겠습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 8,
  "persona": "domain_lead",
  "question_contract": {
    "purpose": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다.",
    "required_points": [
      {
        "key": "domain_distinction",
        "description": "질문한 개념을 구분하고 사용자가 이해할 수 있는 예나 흐름으로 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [
      {
        "kind": "jd_requirement",
        "id": "req-f2930e692aed002d"
      },
      {
        "kind": "jd_requirement",
        "id": "req-3ecf5eda1ba6d284"
      }
    ],
    "evaluation_scope": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [
    "req-f2930e692aed002d",
    "req-3ecf5eda1ba6d284"
  ],
  "evidences": []
}
```

</details>

### 턴 9 — `tech_lead`

**질문:** 작업 scheduler의 시간 기준에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
DB 시각으로 예약 판정을 택했습니다. 작업자별 시계 차이로 같은 작업을 다르게 due 판정하는 일을 줄입니다. 비교한 각 작업자의 로컬 시각은 로컬 시각은 DB 호출이 적지만 시계 오차가 판정에 들어갑니다. 대신 시간 판정이 DB 가용성에 의존합니다. 그리고 DB 시각을 쓴다고 외부 요청의 실제 발생 순서까지 알 수는 없습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 9,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "시간 기준의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "시간 기준의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": [
      "technical_reasoning",
      "communication"
    ]
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

## 기대 판정 — 사람 미검토 draft gold

총 **17개 (turn_id, key)** 쌍입니다. 이 파일에는 대체 허용 단계 목록이 없으므로 strict/acceptable 초안 비교는 같은 단일 `level`과 대조합니다. 이것은 승인된 정답률이 아닙니다. `not_applicable`은 숫자 0과 구분합니다.

| turn_id | key | 초안 level | 초안 근거 | rubric 원문 |
|---|---|---|---|---|
| 1 | `contribution_clarity` | `4` | 작업 scheduler: '저는 due 작업 조회와 lease 갱신 루프를 단독으로 구현했습니다. 작업 함수 작성은 동료가 했고, 큐 관리자 화면도 다른 동료 담당입니다. 작업자와 합의한 경계는 claim 응답에 시도 번호를'라는 이 턴 답변에서 단독 작업, 팀원 작업과 공동 합의 경계를 모두 구분한다. | 협업 지점과 단독 기여를 명확히 구분해 설명한다. |
| 1 | `communication` | `4` | '저는 due 작업 조회와 lease 갱신 루프를 단독으로 구현했습니다. 작업 함수 작성은 동료가 했고, 큐 관리자 화면도 다른 동료 담당입니다. 작업자와 합의한 '라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 2 | `project_understanding` | `0` | 질문된 범위의 답변이 null이다. 다른 턴이나 프로젝트 원문에서 이 턴의 응답을 만들어 보충하지 않고 0으로 초안 판정한다. | 질문을 받았지만 프로젝트의 목적이나 핵심 기능을 설명하지 못한다. |
| 2 | `communication` | `0` | 이 턴은 질문 후 답변이 null이므로 전달된 설명이 없으며, 서비스의 미답변 0 규칙으로 초안 판정한다. | 질문과 무관한 답변을 하거나 의미를 파악하기 어렵다. |
| 3 | `technical_reasoning` | `1` | 작은 due 배치 폴링의 이유를 익숙함과 편의로만 표현해 상황에 맞는 근거가 빈약하다. | 이유를 말하지만 '편해서·많이 써서' 같이 내용이 없는 수준이다. |
| 3 | `communication` | `1` | '작은 due 배치 폴링을 택했습니다. 익숙하고 많이 쓰는 방식이라 편했기 때문입니다.'라는 이 턴의 표현은 질문의 일부만 말해 핵심 설명이 불분명하다. | 질문의 일부에만 답하고 핵심이 불분명하다. |
| 4 | `problem_solving` | `2` | 작업 scheduler: '일부 작업이 완료 뒤에도 다시 실행됐습니다. 오래된 시도의 완료 응답이 뒤늦게 온 것 같아서 완료 시 시도 번호를 확인하게 바꿨고 재실행이 줄어드는 것을 봤습니다. 응답 순서를 통제한 재현이나 비교'라는 이 턴 답변에서 원인 추정이나 수정 일부를 말하나 진단과 검증의 연결이 모호하다. | 해결했다고 말하며 원인이나 방법을 언급하나 모호하거나 일부만 설명한다. |
| 4 | `communication` | `3` | '일부 작업이 완료 뒤에도 다시 실행됐습니다. 오래된 시도의 완료 응답이 뒤늦게 온 것 같아서 완료 시 시도 번호를 확인하게 바꿨고 재실행이 줄어드는 것을 봤습니다'라는 이 턴의 표현은 질문 의도에 맞는 흐름으로 설명한다. 핵심을 먼저 구조화한 최고 단계까지 자동 승격하지 않는다. | 질문 의도에 맞춰 논리적 순서로 답변한다. |
| 5 | `company_job_fit` | `3` | 작업 scheduler: 'JD의 실패 복구 기록 요구에 시도 번호를 남기는 완료 API 경험이 대응합니다. lease가 만료된 뒤 이전 작업자가 보낸 완료 요청을 넣어 새 시도의 상태가 유지되는지 검사했습니다. 실행 지연 '라는 이 턴 답변에서 요구사항과 직접 수행한 경험을 하나의 구체적 사례로 연결한다. | 요구사항과 본인 경험을 구체적 사례로 연결한다. |
| 5 | `communication` | `3` | 'JD의 실패 복구 기록 요구에 시도 번호를 남기는 완료 API 경험이 대응합니다. lease가 만료된 뒤 이전 작업자가 보낸 완료 요청을 넣어 새 시도의 상태가 '라는 이 턴의 표현은 질문 의도에 맞는 흐름으로 설명한다. 핵심을 먼저 구조화한 최고 단계까지 자동 승격하지 않는다. | 질문 의도에 맞춰 논리적 순서로 답변한다. |
| 6 | `technical_reasoning` | `2` | 작업자가 사라져도 기한 후 다른 작업자가 회수합니다라는 구체 근거가 있으나 영구 실행 잠금과의 비교는 하지 않는다. | 근거는 제시하나 대안과의 비교가 없거나 피상적이다. |
| 6 | `communication` | `4` | '기한 있는 lease을 택했습니다. 선택 근거는 다음과 같습니다: 작업자가 사라져도 기한 후 다른 작업자가 회수합니다.'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 7 | `technical_reasoning` | `3` | 작업 ID만으로 완료 처리을 대안으로 인지하고 ID만 쓰면 간단하지만 어느 실행의 결과인지 구분하지 못합니다라는 차이로 선택을 설명하나 선택한 방식의 구체 비용과 한계를 함께 다루지는 않는다. | 대안을 인지하고 선택 이유를 합리적으로 설명한다. |
| 7 | `communication` | `4` | '시도 번호를 조건으로 상태 갱신을 택했습니다. 선택 근거는 다음과 같습니다: 이전 작업자의 늦은 완료가 새 시도를 종료하지 못하게 합니다. 작업 ID만으로 완료 '라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 8 | `communication` | `0` | '오늘 점심 메뉴는 면이었습니다. lease와 완료의 차이 대신 식당 얘기를 계속하겠습니다.'라는 이 턴의 표현은 질문한 설명 대신 무관한 내용 또는 의미를 흐리는 나열·명령을 제시해 의도를 전달하지 못한다. | 질문과 무관한 답변을 하거나 의미를 파악하기 어렵다. |
| 9 | `technical_reasoning` | `4` | 각 작업자의 로컬 시각과 비교하고, 선택 비용 '시간 판정이 DB 가용성에 의존합니다'와 한계 'DB 시각을 쓴다고 외부 요청의 실제 발생 순서까지 알 수는 없습니다'까지 구체적으로 설명한다. | 트레이드오프를 구체적으로 비교하고 한계까지 인지하고 있다. |
| 9 | `communication` | `4` | 'DB 시각으로 예약 판정을 택했습니다. 작업자별 시계 차이로 같은 작업을 다르게 due 판정하는 일을 줄입니다. 비교한 각 작업자의 로컬 시각은 로컬 시각은 DB'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |

<details>
<summary>독립 검토 대기 항목</summary>

```json
{
  "case_id": "b-main-06",
  "version": 1,
  "review": {
    "status": "unreviewed",
    "author": "Codex",
    "reviewer": null,
    "reviewed_at": null,
    "pending_notes": [
      "전체 문답·315개 annotation은 합성 초안이다. 후보 모델 출력이나 Judge로 gold를 만든 것이 아니며 독립 사람 판정 전에는 의미 정답으로 확정하지 않는다.",
      "유일한 U null 사례.",
      "특히 R2의 짧은 선택+이유는 질문의 필수 의도에 답한 경우에만 C4로 초안 판정했다. 선택 이유를 묻는 질문에 방식만 나열한 응답은 C4가 아니다.",
      "인접 단계와 C2/C3/C4 경계는 독립 검토가 필요하다. null은 C0, 의미가 분명한 모름·미회상 선언은 부분 응답 C1로 초안 판정했으며 legacy NA도 사람이 검토해야 한다."
    ]
  }
}
```

</details>

<details>
<summary>전체 평가 rubric·JD·보완자료 (동결 입력)</summary>

```json
{
  "requirements": [
    {
      "id": "req-f2930e692aed002d",
      "category": "required",
      "text": "예약 작업의 실행 지연과 중복 실행 조건을 설명할 수 있어야 한다."
    },
    {
      "id": "req-3ecf5eda1ba6d284",
      "category": "required",
      "text": "실패 복구 절차를 검증 가능한 작업 기록으로 제시해야 한다."
    }
  ],
  "rubrics": {
    "project_understanding": {
      "0": "질문을 받았지만 프로젝트의 목적이나 핵심 기능을 설명하지 못한다.",
      "1": "목적이나 기능을 언급하나 핵심이 빈약하고 구체적인 내용이 없다.",
      "2": "핵심 기능은 설명하나 구조·흐름 설명이 피상적이거나 일부 부정확하다.",
      "3": "핵심 기능과 구조를 대체로 정확히 설명한다.",
      "4": "구조·의존관계·설계 의도까지 근거를 들어 설명한다."
    },
    "technical_reasoning": {
      "0": "질문을 받았지만 이유를 말하지 않거나(방식만 말하는 경우 포함) 모른다고 답한다.",
      "1": "이유를 말하지만 '편해서·많이 써서' 같이 내용이 없는 수준이다.",
      "2": "근거는 제시하나 대안과의 비교가 없거나 피상적이다.",
      "3": "대안을 인지하고 선택 이유를 합리적으로 설명한다.",
      "4": "트레이드오프를 구체적으로 비교하고 한계까지 인지하고 있다."
    },
    "problem_solving": {
      "0": "질문을 받았지만 문제 상황을 구체적으로 떠올리지 못한다.",
      "1": "문제 상황만 말하거나, 구체적인 원인·방법 없이 해결했다고만 말한다.",
      "2": "해결했다고 말하며 원인이나 방법을 언급하나 모호하거나 일부만 설명한다.",
      "3": "문제 원인을 진단하고 해결한 과정을 구체적으로 설명한다.",
      "4": "여러 대안을 검토한 근거와 재발 방지까지 설명한다."
    },
    "communication": {
      "0": "질문과 무관한 답변을 하거나 의미를 파악하기 어렵다.",
      "1": "질문의 일부에만 답하고 핵심이 불분명하다.",
      "2": "질문에는 답하나 설명 순서가 뒤섞여 이해하기 어렵다.",
      "3": "질문 의도에 맞춰 논리적 순서로 답변한다.",
      "4": "핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다."
    },
    "contribution_clarity": {
      "0": "질문을 받았지만 본인이 한 일을 말하지 못한다.",
      "1": "참여했다고만 말하고 팀 성과와 본인 기여를 구분하지 못한다.",
      "2": "본인이 한 일은 말하나 범위와 결과가 불명확하다.",
      "3": "본인이 담당한 부분과 그 근거를 구체적으로 설명한다.",
      "4": "협업 지점과 단독 기여를 명확히 구분해 설명한다."
    },
    "company_job_fit": {
      "0": "질문을 받았지만 무엇을 했는지 말하지 않거나(경험이 있다는 말만 하는 경우 포함) 모른다고 답한다.",
      "1": "요구사항이나 경험 중 하나만 구체적으로 언급한다.",
      "2": "요구사항과 경험을 둘 다 언급하며 연결하나 근거가 빈약하거나 일반론에 그친다.",
      "3": "요구사항과 본인 경험을 구체적 사례로 연결한다.",
      "4": "요구사항별로 대응하는 경험과 한계까지 균형 있게 설명한다."
    }
  },
  "tool_results": [
    {
      "turn_id": "2",
      "result": {
        "status": "found",
        "items": [
          {
            "evidence_id": "ev-10822efcc910b89b",
            "repository_id": "repo-10822efcc910b89b",
            "git_ref": "19de02ff345ebd610bcfded46b16dd6471862773",
            "source_kind": "repository",
            "path": "docs/project-context.md",
            "metadata_key": null,
            "content": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.",
            "tool_name": "repository_reader",
            "summary": "제공된 프로젝트 설명의 제한된 구간",
            "start_line": 1,
            "end_line": 1
          }
        ],
        "searched_scope": [
          "docs/project-context.md:1"
        ],
        "limitations": [
          "이 구간 이외 소스와 실행 결과는 확인하지 않았다."
        ],
        "error_code": null
      }
    }
  ],
  "limitations": [
    "제공된 문서 구간과 저장된 관측 외의 구현·실행·기여 사실은 확인되지 않았다."
  ],
  "supplemental_sources": [
    {
      "source_id": "doc-10822efcc910b89b",
      "kind": "document_claim",
      "content": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.\n설계 기록: 시도 번호를 조건으로 상태 갱신. 이전 작업자의 늦은 완료가 새 시도를 종료하지 못하게 합니다",
      "location": "design-notes.md#decision-record",
      "version": "8a68d6d519315d755784aa8bc3c91998b0cb44bd005e7550a47c8980b58e2138",
      "limitations": [
        "설계 기록은 구현 존재나 개인 기여를 독립 확인한 자료가 아니다."
      ],
      "title": "작업 scheduler 설계 기록",
      "retrieved_at": null
    }
  ],
  "source_notes": []
}
```

</details>

<details>
<summary>동결 입력 JSON 전체 — gold는 포함하지 않는 별도 입력 파일</summary>

```json
{
  "case_id": "b-main-06",
  "version": 1,
  "control": {
    "kind": "report",
    "split": "dev",
    "source_group_id": "sg-b-main-06",
    "synthetic": true
  },
  "payload": {
    "service_task": "report",
    "service_input": {
      "turns": [
        {
          "turn_no": 1,
          "persona": "hr_manager",
          "question": "작업 scheduler에서 본인이 한 일과 팀원이 한 일을 구분하고, 작업 근거와 협업 지점을 소개해 주세요.",
          "question_contract": {
            "purpose": "개인 담당과 협업 경계를 설명한다.",
            "required_points": [
              {
                "key": "own_scope",
                "description": "직접 수행한 작업과 확인할 수 있는 작업 근거를 설명한다."
              },
              {
                "key": "boundary",
                "description": "팀원의 담당과 공동으로 결정한 부분을 구분한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "개인 담당과 협업 경계를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "contribution_clarity",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "저는 due 작업 조회와 lease 갱신 루프를 단독으로 구현했습니다. 작업 함수 작성은 동료가 했고, 큐 관리자 화면도 다른 동료 담당입니다. 작업자와 합의한 경계는 claim 응답에 시도 번호를 포함하는 것이었고, 저는 그 번호를 검사하는 완료 API와 시간 이동 테스트를 작성했습니다."
        },
        {
          "turn_no": 2,
          "persona": "tech_lead",
          "question": "작업 scheduler의 목적과 핵심 기능을 요청·처리·저장 흐름으로 설명하고 구성요소가 어떻게 의존하는지 말해 주세요.",
          "question_contract": {
            "purpose": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다.",
            "required_points": [
              {
                "key": "core_flow",
                "description": "사용자 입력부터 결과까지 구성요소의 연결을 설명한다."
              },
              {
                "key": "dependency",
                "description": "구성요소의 의존 관계와 그 의도를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [
              {
                "kind": "evidence",
                "id": "ev-10822efcc910b89b"
              }
            ],
            "evaluation_scope": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "project_understanding",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [
            {
              "id": "ev-10822efcc910b89b",
              "repository_id": "repo-10822efcc910b89b",
              "git_ref": "19de02ff345ebd610bcfded46b16dd6471862773",
              "source_type": "repository",
              "path": "docs/project-context.md",
              "metadata_key": null,
              "snippet": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.",
              "tool_name": "repository_reader",
              "summary": "제공된 프로젝트 설명의 제한된 구간",
              "start_line": 1,
              "end_line": 1
            }
          ],
          "answer": null
        },
        {
          "turn_no": 3,
          "persona": "tech_lead",
          "question": "작업 scheduler의 예약 조회에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "예약 조회의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "예약 조회의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "technical_reasoning",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "작은 due 배치 폴링을 택했습니다. 익숙하고 많이 쓰는 방식이라 편했기 때문입니다."
        },
        {
          "turn_no": 4,
          "persona": "tech_lead",
          "question": "작업 scheduler에서 떠올릴 수 있는 구체적 문제 한 가지와 원인 확인, 수정, 검증 과정을 설명해 주세요. 검토한 대안이나 재발 방지가 있다면 함께 설명해 주세요.",
          "question_contract": {
            "purpose": "하나의 문제를 식별하고 해결한 과정을 설명한다.",
            "required_points": [
              {
                "key": "diagnosis",
                "description": "문제 증상과 원인을 확인한 관찰을 설명한다."
              },
              {
                "key": "resolution",
                "description": "수정 방법과 검증 과정을 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "하나의 문제를 식별하고 해결한 과정을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "problem_solving",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "일부 작업이 완료 뒤에도 다시 실행됐습니다. 오래된 시도의 완료 응답이 뒤늦게 온 것 같아서 완료 시 시도 번호를 확인하게 바꿨고 재실행이 줄어드는 것을 봤습니다. 응답 순서를 통제한 재현이나 비교 로그는 남기지 못했습니다."
        },
        {
          "turn_no": 5,
          "persona": "domain_lead",
          "question": "제공된 두 JD 요구사항을 보고 작업 scheduler에서의 본인 경험이 어떻게 대응하는지 사례로 연결해 주세요. 경험 범위의 한계도 함께 말해 주세요.",
          "question_contract": {
            "purpose": "제공된 JD 요구사항과 개인 경험을 연결한다.",
            "required_points": [
              {
                "key": "experience_link",
                "description": "요구사항에 대응하는 직접 수행 경험과 사례를 설명한다."
              },
              {
                "key": "limits",
                "description": "경험으로 뒷받침할 수 있는 범위를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [
              {
                "kind": "jd_requirement",
                "id": "req-f2930e692aed002d"
              },
              {
                "kind": "jd_requirement",
                "id": "req-3ecf5eda1ba6d284"
              }
            ],
            "evaluation_scope": "제공된 JD 요구사항과 개인 경험을 연결한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "company_job_fit",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [
            "req-f2930e692aed002d",
            "req-3ecf5eda1ba6d284"
          ],
          "evidences": [],
          "answer": "JD의 실패 복구 기록 요구에 시도 번호를 남기는 완료 API 경험이 대응합니다. lease가 만료된 뒤 이전 작업자가 보낸 완료 요청을 넣어 새 시도의 상태가 유지되는지 검사했습니다. 실행 지연 자체보다는 복구 중 상태를 잘못 끝내지 않는 부분을 검증한 예입니다."
        },
        {
          "turn_no": 6,
          "persona": "tech_lead",
          "question": "작업 scheduler의 실행 소유권에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "실행 소유권의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "실행 소유권의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "technical_reasoning",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "기한 있는 lease을 택했습니다. 선택 근거는 다음과 같습니다: 작업자가 사라져도 기한 후 다른 작업자가 회수합니다."
        },
        {
          "turn_no": 7,
          "persona": "tech_lead",
          "question": "작업 scheduler의 완료 검증에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "완료 검증의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [
              {
                "kind": "document_claim",
                "id": "doc-10822efcc910b89b"
              }
            ],
            "evaluation_scope": "완료 검증의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "technical_reasoning",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "시도 번호를 조건으로 상태 갱신을 택했습니다. 선택 근거는 다음과 같습니다: 이전 작업자의 늦은 완료가 새 시도를 종료하지 못하게 합니다. 작업 ID만으로 완료 처리도 검토했습니다. ID만 쓰면 간단하지만 어느 실행의 결과인지 구분하지 못합니다."
        },
        {
          "turn_no": 8,
          "persona": "domain_lead",
          "question": "작업이 claim됐다는 것과 완료됐다는 것은 사용자에게 어떻게 다른 상태인가요?",
          "question_contract": {
            "purpose": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다.",
            "required_points": [
              {
                "key": "domain_distinction",
                "description": "질문한 개념을 구분하고 사용자가 이해할 수 있는 예나 흐름으로 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [
              {
                "kind": "jd_requirement",
                "id": "req-f2930e692aed002d"
              },
              {
                "kind": "jd_requirement",
                "id": "req-3ecf5eda1ba6d284"
              }
            ],
            "evaluation_scope": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [
            "req-f2930e692aed002d",
            "req-3ecf5eda1ba6d284"
          ],
          "evidences": [],
          "answer": "오늘 점심 메뉴는 면이었습니다. lease와 완료의 차이 대신 식당 얘기를 계속하겠습니다."
        },
        {
          "turn_no": 9,
          "persona": "tech_lead",
          "question": "작업 scheduler의 시간 기준에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "시간 기준의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "시간 기준의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": [
              "technical_reasoning",
              "communication"
            ]
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "DB 시각으로 예약 판정을 택했습니다. 작업자별 시계 차이로 같은 작업을 다르게 due 판정하는 일을 줄입니다. 비교한 각 작업자의 로컬 시각은 로컬 시각은 DB 호출이 적지만 시계 오차가 판정에 들어갑니다. 대신 시간 판정이 DB 가용성에 의존합니다. 그리고 DB 시각을 쓴다고 외부 요청의 실제 발생 순서까지 알 수는 없습니다."
        }
      ],
      "requirements": [
        {
          "id": "req-f2930e692aed002d",
          "category": "required",
          "text": "예약 작업의 실행 지연과 중복 실행 조건을 설명할 수 있어야 한다."
        },
        {
          "id": "req-3ecf5eda1ba6d284",
          "category": "required",
          "text": "실패 복구 절차를 검증 가능한 작업 기록으로 제시해야 한다."
        }
      ],
      "rubrics": {
        "project_understanding": {
          "0": "질문을 받았지만 프로젝트의 목적이나 핵심 기능을 설명하지 못한다.",
          "1": "목적이나 기능을 언급하나 핵심이 빈약하고 구체적인 내용이 없다.",
          "2": "핵심 기능은 설명하나 구조·흐름 설명이 피상적이거나 일부 부정확하다.",
          "3": "핵심 기능과 구조를 대체로 정확히 설명한다.",
          "4": "구조·의존관계·설계 의도까지 근거를 들어 설명한다."
        },
        "technical_reasoning": {
          "0": "질문을 받았지만 이유를 말하지 않거나(방식만 말하는 경우 포함) 모른다고 답한다.",
          "1": "이유를 말하지만 '편해서·많이 써서' 같이 내용이 없는 수준이다.",
          "2": "근거는 제시하나 대안과의 비교가 없거나 피상적이다.",
          "3": "대안을 인지하고 선택 이유를 합리적으로 설명한다.",
          "4": "트레이드오프를 구체적으로 비교하고 한계까지 인지하고 있다."
        },
        "problem_solving": {
          "0": "질문을 받았지만 문제 상황을 구체적으로 떠올리지 못한다.",
          "1": "문제 상황만 말하거나, 구체적인 원인·방법 없이 해결했다고만 말한다.",
          "2": "해결했다고 말하며 원인이나 방법을 언급하나 모호하거나 일부만 설명한다.",
          "3": "문제 원인을 진단하고 해결한 과정을 구체적으로 설명한다.",
          "4": "여러 대안을 검토한 근거와 재발 방지까지 설명한다."
        },
        "communication": {
          "0": "질문과 무관한 답변을 하거나 의미를 파악하기 어렵다.",
          "1": "질문의 일부에만 답하고 핵심이 불분명하다.",
          "2": "질문에는 답하나 설명 순서가 뒤섞여 이해하기 어렵다.",
          "3": "질문 의도에 맞춰 논리적 순서로 답변한다.",
          "4": "핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다."
        },
        "contribution_clarity": {
          "0": "질문을 받았지만 본인이 한 일을 말하지 못한다.",
          "1": "참여했다고만 말하고 팀 성과와 본인 기여를 구분하지 못한다.",
          "2": "본인이 한 일은 말하나 범위와 결과가 불명확하다.",
          "3": "본인이 담당한 부분과 그 근거를 구체적으로 설명한다.",
          "4": "협업 지점과 단독 기여를 명확히 구분해 설명한다."
        },
        "company_job_fit": {
          "0": "질문을 받았지만 무엇을 했는지 말하지 않거나(경험이 있다는 말만 하는 경우 포함) 모른다고 답한다.",
          "1": "요구사항이나 경험 중 하나만 구체적으로 언급한다.",
          "2": "요구사항과 경험을 둘 다 언급하며 연결하나 근거가 빈약하거나 일반론에 그친다.",
          "3": "요구사항과 본인 경험을 구체적 사례로 연결한다.",
          "4": "요구사항별로 대응하는 경험과 한계까지 균형 있게 설명한다."
        }
      },
      "tool_results": [
        {
          "turn_id": "2",
          "result": {
            "status": "found",
            "items": [
              {
                "evidence_id": "ev-10822efcc910b89b",
                "repository_id": "repo-10822efcc910b89b",
                "git_ref": "19de02ff345ebd610bcfded46b16dd6471862773",
                "source_kind": "repository",
                "path": "docs/project-context.md",
                "metadata_key": null,
                "content": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.",
                "tool_name": "repository_reader",
                "summary": "제공된 프로젝트 설명의 제한된 구간",
                "start_line": 1,
                "end_line": 1
              }
            ],
            "searched_scope": [
              "docs/project-context.md:1"
            ],
            "limitations": [
              "이 구간 이외 소스와 실행 결과는 확인하지 않았다."
            ],
            "error_code": null
          }
        }
      ],
      "limitations": [
        "제공된 문서 구간과 저장된 관측 외의 구현·실행·기여 사실은 확인되지 않았다."
      ],
      "supplemental_sources": [
        {
          "source_id": "doc-10822efcc910b89b",
          "kind": "document_claim",
          "content": "예약 시각이 된 작업을 claim하고 lease 만료 시 재할당하는 스케줄러 실험이다. 작업 ID별 시도 번호를 저장하며 실행 결과를 받은 시도만 완료 처리한다.\n설계 기록: 시도 번호를 조건으로 상태 갱신. 이전 작업자의 늦은 완료가 새 시도를 종료하지 못하게 합니다",
          "location": "design-notes.md#decision-record",
          "version": "8a68d6d519315d755784aa8bc3c91998b0cb44bd005e7550a47c8980b58e2138",
          "limitations": [
            "설계 기록은 구현 존재나 개인 기여를 독립 확인한 자료가 아니다."
          ],
          "title": "작업 scheduler 설계 기록",
          "retrieved_at": null
        }
      ],
      "source_notes": []
    }
  }
}
```

</details>

## 6개 후보 슬롯의 실제 응답과 기술 판정

상태와 기술 오류는 기록을 그대로 옮겼습니다. HTTP 성공, 서비스 형식/계약 검증, 의미 품질은 서로 다른 관찰입니다. A의 plan 뒤 review는 계획된 단계이며 그 자체를 재시도로 세지 않습니다. 모든 의미 기준은 `unreviewed`, 승인된 정확도 분모는 0입니다.

| 후보 슬롯 | 최종 상태 | 물리 요청 수 | 최종 결과 행 | 기술 오류/원인 |
|---|---|---:|---|---|
| `gpt-6.1-sol` | **성공** (`succeeded`) | 1 | 있음 | 기록된 실패 없음 |
| `gemini-3.8-flash` | **성공** (`succeeded`) | 1 | 있음 | 기록된 실패 없음 |
| `gemini-4-argon` | **성공** (`succeeded`) | 1 | 있음 | 기록된 실패 없음 |
| `claude-haiku-5-5` | **실패** (`failed`) | 1 | 있음 | contract_validation_failed_after_provider_stop |
| `claude-sonnet-5-5` | **미실행** (`not_executed`) | 0 | 없음 | 기록된 실패 없음 |
| `gpt-6-luna` | **성공** (`succeeded`) | 1 | 있음 | 기록된 실패 없음 |


### 각 (턴, key)의 초안 gold와 실제 단계

표의 `—`는 미실행/유효한 최종 판정 없음이며 0점이 아닙니다. 별도 실패 요청의 부분 텍스트는 판정값으로 보충하지 않았습니다.

| 턴 / key | draft gold | `gpt-6.1-sol` | `gemini-3.8-flash` | `gemini-4-argon` | `claude-haiku-5-5` | `claude-sonnet-5-5` | `gpt-6-luna` |
|---|---|---|---|---|---|---|---|
| 1 / `contribution_clarity` | `4` | `4` | `4` | `4` | — | — | `4` |
| 1 / `communication` | `4` | `4` | `4` | `4` | — | — | `4` |
| 2 / `project_understanding` | `0` | `0` | `0` | `0` | — | — | `0` |
| 2 / `communication` | `0` | `0` | `0` | `0` | — | — | `0` |
| 3 / `technical_reasoning` | `1` | `1` | `1` | `1` | — | — | `1` |
| 3 / `communication` | `1` | `3` ≠ | `1` | `1` | — | — | `3` ≠ |
| 4 / `problem_solving` | `2` | `2` | `2` | `2` | — | — | `2` |
| 4 / `communication` | `3` | `4` ≠ | `3` | `3` | — | — | `3` |
| 5 / `company_job_fit` | `3` | `3` | `3` | `4` ≠ | — | — | `3` |
| 5 / `communication` | `3` | `4` ≠ | `3` | `4` ≠ | — | — | `4` ≠ |
| 6 / `technical_reasoning` | `2` | `2` | `2` | `2` | — | — | `2` |
| 6 / `communication` | `4` | `4` | `3` ≠ | `3` ≠ | — | — | `3` ≠ |
| 7 / `technical_reasoning` | `3` | `3` | `3` | `3` | — | — | `4` ≠ |
| 7 / `communication` | `4` | `4` | `4` | `3` ≠ | — | — | `4` |
| 8 / `communication` | `0` | `0` | `0` | `0` | — | — | `0` |
| 9 / `technical_reasoning` | `4` | `4` | `4` | `4` | — | — | `4` |
| 9 / `communication` | `4` | `4` | `4` | `4` | — | — | `4` |


### 초안과의 기계적 비교 — 승인된 정확도 아님

| 후보 슬롯 | strict = acceptable 초안 일치 | 수치 단계 MAE | 코드 환산 total (후보 / draft) |
|---|---|---|---|
| `gpt-6.1-sol` | 14/17 | 0.235294 | 55 / 53 |
| `gemini-3.8-flash` | 16/17 | 0.058824 | 53 / 53 |
| `gemini-4-argon` | 13/17 | 0.235294 | 56 / 53 |
| `claude-haiku-5-5` | 비교 불가 (실패) | — | — |
| `claude-sonnet-5-5` | 비교 불가 (미실행) | — | — |
| `gpt-6-luna` | 13/17 | 0.294118 | 55 / 53 |


MAE는 양쪽 값이 숫자인 쌍만 사용합니다. `not_applicable` 불일치는 위 쌍별 표에 남으며 숫자 MAE에서 빠집니다. total은 모델이 출력한 점수가 아니라 원본 final-analysis의 코드 환산 진단 값입니다.


### 후보 `gpt-6.1-sol` — 성공

회계 식별자: `gpt-6.1-sol::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-2.json) — `cases`에서 `b-main-06` 식별자로 찾습니다.

**최종 서비스 응답 (실제 기록):**

```json
{
  "judgments": [
    {
      "turn_id": "1",
      "key": "contribution_clarity",
      "level": 4
    },
    {
      "turn_id": "1",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 0
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "5",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 4
    }
  ]
}
```

<details>
<summary>기술 검증·오류·입력/출력 결합 기록</summary>

```json
{
  "status": "succeeded",
  "failure": null,
  "quality": "excluded_unreviewed",
  "review_status": "unreviewed"
}
```

</details>


#### 요청 elice-dev30-10usd-20261111-recovery-2::attempt-25 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-2::attempt-25`. lifetime ID `attempt-27`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-2-raw/response-0003.json) · SHA-256 `1a85f6508dc744c6cdaf2c68dba177b9f377dc7dc94e6984cbf3c32bd7db6b52`

<details>
<summary>기술 판정과 종료/잘림 표식</summary>

```json
{
  "attempt": {
    "http_status": 200,
    "task_stage": null,
    "task_schema_version": "1",
    "task_prompt_version": "report_score_v3",
    "task_stage_attempt_number": null,
    "intentional_director_review": false,
    "is_retry": false,
    "is_failed_attempt": false,
    "error_stage": null,
    "error_code": null,
    "technical_failure_cause": null,
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 7680,
    "output_tokens": 442,
    "cost_status": "bounded",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "responses",
    "finish_reasons": [],
    "response_status": "completed",
    "incomplete_reason": null,
    "truncated": false,
    "reasoning_output_tokens": 187,
    "output_tokens_observed": 442,
    "non_reasoning_output_tokens": 255,
    "visible_output_characters": 874,
    "technical_cause": "provider_reported_completion",
    "explicit_schema_request_rejection": false,
    "explicit_strict_schema_incompatibility": false
  }
}
```

</details>

**요청에서 실제 생성된 공개 텍스트/거부 필드 (잘린 문자열도 그대로):**

<details>
<summary>원본 공개 생성 필드 전체</summary>

```json
[
  {
    "source": "output[1]",
    "role": "assistant",
    "status": "completed",
    "content": [
      {
        "type": "output_text",
        "annotations": [],
        "logprobs": [],
        "text": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":0},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":1},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":2},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":3},{\"turn_id\":\"7\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"8\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"9\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"9\",\"key\":\"communication\",\"level\":4}]}"
      }
    ]
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":0},{"turn_id":"2","key":"communication","level":0},{"turn_id":"3","key":"technical_reasoning","level":1},{"turn_id":"3","key":"communication","level":3},{"turn_id":"4","key":"problem_solving","level":2},{"turn_id":"4","key":"communication","level":4},{"turn_id":"5","key":"company_job_fit","level":3},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"technical_reasoning","level":2},{"turn_id":"6","key":"communication","level":4},{"turn_id":"7","key":"technical_reasoning","level":3},{"turn_id":"7","key":"communication","level":4},{"turn_id":"8","key":"communication","level":0},{"turn_id":"9","key":"technical_reasoning","level":4},{"turn_id":"9","key":"communication","level":4}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-2.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gpt-6.1-sol::cases/answer/main-v1::b-main-06",
  "model_id": "gpt-6.1-sol",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "gpt-6.1-sol-2",
  "status": "succeeded",
  "fresh_result_present": false,
  "display_result_present": true,
  "result_reused": true,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-2",
  "reused_output_sha256": "74a2a1b188add85ade44b7b62fcfe27c7689cd8ed5896a481da60f831fe5906b",
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 8688.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-2::attempt-25"
  ],
  "fresh_attempt_ids": [],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": false,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.0185404",
    "cost_upper_usd": "0.0187278",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.0185404",
    "known_tariff_upper_subtotal_usd": "0.0187278",
    "unknown_attempts": 0,
    "bounded_attempts": 1,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 7680,
    "output_known_subtotal": 442,
    "input_total": 7680,
    "output_total": 442,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 17,
    "strict_matches": 14,
    "acceptable_matches": 14,
    "na_mismatches": 0,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 4,
    "case_id": "b-main-06",
    "corpus": "cases/answer/main-v1",
    "predicted": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 68,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 55
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 58,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 53
    },
    "absolute_total_deviation": 2,
    "key_absolute_deviations": [
      0,
      0,
      0,
      10,
      0,
      0
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `gemini-3.8-flash` — 성공

회계 식별자: `gemini-3.8-flash::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-2.json) — `cases`에서 `b-main-06` 식별자로 찾습니다.

**최종 서비스 응답 (실제 기록):**

```json
{
  "judgments": [
    {
      "turn_id": "1",
      "key": "contribution_clarity",
      "level": 4
    },
    {
      "turn_id": "1",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 0
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 1
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 4
    }
  ]
}
```

<details>
<summary>기술 검증·오류·입력/출력 결합 기록</summary>

```json
{
  "status": "succeeded",
  "failure": null,
  "quality": "excluded_unreviewed",
  "review_status": "unreviewed"
}
```

</details>


#### 요청 elice-dev30-10usd-20261111-recovery-3::attempt-17 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-3::attempt-17`. lifetime ID `attempt-47`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-2-raw/response-0003.json) · SHA-256 `13f6e8de7aef45cf65276d309db819d6ee4b768c8e5e9efac310ea3a58a4b56e`

<details>
<summary>기술 판정과 종료/잘림 표식</summary>

```json
{
  "attempt": {
    "http_status": 200,
    "task_stage": null,
    "task_schema_version": "1",
    "task_prompt_version": "report_score_v3",
    "task_stage_attempt_number": null,
    "intentional_director_review": false,
    "is_retry": false,
    "is_failed_attempt": false,
    "error_stage": null,
    "error_code": null,
    "technical_failure_cause": null,
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 6520,
    "output_tokens": 563,
    "cost_status": "confirmed",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "chat_completions",
    "finish_reasons": [
      "stop"
    ],
    "response_status": null,
    "incomplete_reason": null,
    "truncated": false,
    "reasoning_output_tokens": null,
    "output_tokens_observed": 563,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 1460,
    "technical_cause": "provider_reported_completion",
    "explicit_schema_request_rejection": false,
    "explicit_strict_schema_incompatibility": false
  }
}
```

</details>

**요청에서 실제 생성된 공개 텍스트/거부 필드 (잘린 문자열도 그대로):**

<details>
<summary>원본 공개 생성 필드 전체</summary>

```json
[
  {
    "source": "choices[0].message",
    "role": "assistant",
    "content": "{\n  \"judgments\": [\n    {\n      \"turn_id\": \"1\",\n      \"key\": \"contribution_clarity\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"1\",\n      \"key\": \"communication\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"project_understanding\",\n      \"level\": 0\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"communication\",\n      \"level\": 0\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 1\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"communication\",\n      \"level\": 1\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"problem_solving\",\n      \"level\": 2\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"5\",\n      \"key\": \"company_job_fit\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"5\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 2\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"communication\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"8\",\n      \"key\": \"communication\",\n      \"level\": 0\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"communication\",\n      \"level\": 4\n    }\n  ]\n}",
    "refusal": null
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{
  "judgments": [
    {
      "turn_id": "1",
      "key": "contribution_clarity",
      "level": 4
    },
    {
      "turn_id": "1",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 0
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 1
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 4
    }
  ]
}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-2.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gemini-3.8-flash::cases/answer/main-v1::b-main-06",
  "model_id": "gemini-3.8-flash",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "gemini-3.8-flash-2",
  "status": "succeeded",
  "fresh_result_present": false,
  "display_result_present": true,
  "result_reused": true,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-3",
  "reused_output_sha256": "fb6557c69896351ff629dc97f008da985d42fe0491a829f5a2c318faab31d3ae",
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 5120.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-3::attempt-17"
  ],
  "fresh_attempt_ids": [],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": false,
  "cost": {
    "status": "confirmed",
    "cost_usd": "0.00700125",
    "cost_lower_usd": "0.00700125",
    "cost_upper_usd": "0.00700125",
    "known_confirmed_subtotal_usd": "0.00700125",
    "known_tariff_lower_subtotal_usd": "0.00700125",
    "known_tariff_upper_subtotal_usd": "0.00700125",
    "unknown_attempts": 0,
    "bounded_attempts": 0,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 6520,
    "output_known_subtotal": 563,
    "input_total": 6520,
    "output_total": 563,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 17,
    "strict_matches": 16,
    "acceptable_matches": 16,
    "na_mismatches": 0,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 1,
    "case_id": "b-main-06",
    "corpus": "cases/answer/main-v1",
    "predicted": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 56,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 53
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 58,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 53
    },
    "absolute_total_deviation": 0,
    "key_absolute_deviations": [
      0,
      0,
      0,
      2,
      0,
      0
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `gemini-4-argon` — 성공

회계 식별자: `gemini-4-argon::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-2.json) — `cases`에서 `b-main-06` 식별자로 찾습니다.

**최종 서비스 응답 (실제 기록):**

```json
{
  "judgments": [
    {
      "turn_id": "1",
      "key": "contribution_clarity",
      "level": 4
    },
    {
      "turn_id": "1",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 0
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 1
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "company_job_fit",
      "level": 4
    },
    {
      "turn_id": "5",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 4
    }
  ]
}
```

<details>
<summary>기술 검증·오류·입력/출력 결합 기록</summary>

```json
{
  "status": "succeeded",
  "failure": null,
  "quality": "excluded_unreviewed",
  "review_status": "unreviewed"
}
```

</details>


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-3 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-3`. lifetime ID `attempt-73`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-2-raw/response-0003.json) · SHA-256 `f9918d9a9720b3923720963214e1a6b95f27751954abfdb534bff081695b87c0`

<details>
<summary>기술 판정과 종료/잘림 표식</summary>

```json
{
  "attempt": {
    "http_status": 200,
    "task_stage": null,
    "task_schema_version": "1",
    "task_prompt_version": "report_score_v3",
    "task_stage_attempt_number": null,
    "intentional_director_review": false,
    "is_retry": false,
    "is_failed_attempt": false,
    "error_stage": null,
    "error_code": null,
    "technical_failure_cause": null,
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 6498,
    "output_tokens": 277,
    "cost_status": "confirmed",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "chat_completions",
    "finish_reasons": [
      "stop"
    ],
    "response_status": null,
    "incomplete_reason": null,
    "truncated": false,
    "reasoning_output_tokens": null,
    "output_tokens_observed": 277,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 874,
    "technical_cause": "provider_reported_completion",
    "explicit_schema_request_rejection": false,
    "explicit_strict_schema_incompatibility": false
  }
}
```

</details>

**요청에서 실제 생성된 공개 텍스트/거부 필드 (잘린 문자열도 그대로):**

<details>
<summary>원본 공개 생성 필드 전체</summary>

```json
[
  {
    "source": "choices[0].message",
    "role": "assistant",
    "content": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":0},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":1},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":1},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":2},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":4},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":3},{\"turn_id\":\"7\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"8\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"9\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"9\",\"key\":\"communication\",\"level\":4}]}",
    "refusal": null
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":0},{"turn_id":"2","key":"communication","level":0},{"turn_id":"3","key":"technical_reasoning","level":1},{"turn_id":"3","key":"communication","level":1},{"turn_id":"4","key":"problem_solving","level":2},{"turn_id":"4","key":"communication","level":3},{"turn_id":"5","key":"company_job_fit","level":4},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"technical_reasoning","level":2},{"turn_id":"6","key":"communication","level":3},{"turn_id":"7","key":"technical_reasoning","level":3},{"turn_id":"7","key":"communication","level":3},{"turn_id":"8","key":"communication","level":0},{"turn_id":"9","key":"technical_reasoning","level":4},{"turn_id":"9","key":"communication","level":4}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-2.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gemini-4-argon::cases/answer/main-v1::b-main-06",
  "model_id": "gemini-4-argon",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "gemini-4-argon-2",
  "status": "succeeded",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 14460.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-3"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "confirmed",
    "cost_usd": "0.015766",
    "cost_lower_usd": "0.015766",
    "cost_upper_usd": "0.015766",
    "known_confirmed_subtotal_usd": "0.015766",
    "known_tariff_lower_subtotal_usd": "0.015766",
    "known_tariff_upper_subtotal_usd": "0.015766",
    "unknown_attempts": 0,
    "bounded_attempts": 0,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 6498,
    "output_known_subtotal": 277,
    "input_total": 6498,
    "output_total": 277,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 17,
    "strict_matches": 13,
    "acceptable_matches": 13,
    "na_mismatches": 0,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 4,
    "case_id": "b-main-06",
    "corpus": "cases/answer/main-v1",
    "predicted": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 56,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 56
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 58,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 53
    },
    "absolute_total_deviation": 3,
    "key_absolute_deviations": [
      0,
      0,
      0,
      2,
      0,
      20
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `claude-haiku-5-5` — 실패

회계 식별자: `claude-haiku-5-5::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-2.json) — `cases`에서 `b-main-06` 식별자로 찾습니다.

**최종 서비스 응답 (실제 기록):**

```json
null
```

<details>
<summary>기술 검증·오류·입력/출력 결합 기록</summary>

```json
{
  "status": "failed",
  "failure": {
    "stage": "semantic",
    "error_code": "report_score_unscorable",
    "reason_summary": "No scorable turn.",
    "provider_status": null,
    "provider_cause": null,
    "manual_retryable": null
  },
  "quality": "excluded_unreviewed",
  "review_status": "unreviewed"
}
```

</details>


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-25 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-25`. lifetime ID `attempt-95`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-2-raw/response-0003.json) · SHA-256 `6283eab044bc2853a64ba937e757afbec256120a4404ebf91c2b3cafb2c081ec`

<details>
<summary>기술 판정과 종료/잘림 표식</summary>

```json
{
  "attempt": {
    "http_status": 200,
    "task_stage": null,
    "task_schema_version": "1",
    "task_prompt_version": "report_score_v3",
    "task_stage_attempt_number": null,
    "intentional_director_review": false,
    "is_retry": false,
    "is_failed_attempt": true,
    "error_stage": "semantic",
    "error_code": "llm_failed",
    "technical_failure_cause": "contract_validation_failed_after_provider_stop",
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "failed",
    "input_tokens": 13393,
    "output_tokens": 416,
    "cost_status": "bounded",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "chat_completions",
    "finish_reasons": [
      "stop"
    ],
    "response_status": null,
    "incomplete_reason": null,
    "truncated": false,
    "reasoning_output_tokens": null,
    "output_tokens_observed": 416,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 991,
    "technical_cause": "provider_reported_completion",
    "explicit_schema_request_rejection": false,
    "explicit_strict_schema_incompatibility": false
  }
}
```

</details>

**요청에서 실제 생성된 공개 텍스트/거부 필드 (잘린 문자열도 그대로):**

<details>
<summary>원본 공개 생성 필드 전체</summary>

```json
[
  {
    "source": "choices[0].message",
    "role": "assistant",
    "content": "{\"judgments\": [{\"turn_id\": \"1\", \"key\": \"contribution_clarity\", \"level\": 4}, {\"turn_id\": \"1\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"2\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"2\", \"key\": \"communication\", \"level\": 0}, {\"turn_id\": \"3\", \"key\": \"technical_reasoning\", \"level\": 1}, {\"turn_id\": \"3\", \"key\": \"communication\", \"level\": 2}, {\"turn_id\": \"4\", \"key\": \"problem_solving\", \"level\": 2}, {\"turn_id\": \"4\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"5\", \"key\": \"company_job_fit\", \"level\": 3}, {\"turn_id\": \"5\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"6\", \"key\": \"technical_reasoning\", \"level\": 2}, {\"turn_id\": \"6\", \"key\": \"communication\", \"level\": 2}, {\"turn_id\": \"7\", \"key\": \"technical_reasoning\", \"level\": 3}, {\"turn_id\": \"7\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"8\", \"key\": \"communication\", \"level\": 0}, {\"turn_id\": \"9\", \"key\": \"technical_reasoning\", \"level\": 4}, {\"turn_id\": \"9\", \"key\": \"communication\", \"level\": 2}]}",
    "refusal": null
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments": [{"turn_id": "1", "key": "contribution_clarity", "level": 4}, {"turn_id": "1", "key": "communication", "level": 3}, {"turn_id": "2", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "2", "key": "communication", "level": 0}, {"turn_id": "3", "key": "technical_reasoning", "level": 1}, {"turn_id": "3", "key": "communication", "level": 2}, {"turn_id": "4", "key": "problem_solving", "level": 2}, {"turn_id": "4", "key": "communication", "level": 3}, {"turn_id": "5", "key": "company_job_fit", "level": 3}, {"turn_id": "5", "key": "communication", "level": 3}, {"turn_id": "6", "key": "technical_reasoning", "level": 2}, {"turn_id": "6", "key": "communication", "level": 2}, {"turn_id": "7", "key": "technical_reasoning", "level": 3}, {"turn_id": "7", "key": "communication", "level": 3}, {"turn_id": "8", "key": "communication", "level": 0}, {"turn_id": "9", "key": "technical_reasoning", "level": 4}, {"turn_id": "9", "key": "communication", "level": 2}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-2.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "claude-haiku-5-5::cases/answer/main-v1::b-main-06",
  "model_id": "claude-haiku-5-5",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "claude-haiku-5-5-2",
  "status": "failed",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 2095.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-25"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.0011842",
    "cost_upper_usd": "0.0025235",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.0011842",
    "known_tariff_upper_subtotal_usd": "0.0025235",
    "unknown_attempts": 0,
    "bounded_attempts": 1,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 13393,
    "output_known_subtotal": 416,
    "input_total": 13393,
    "output_total": 416,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `claude-sonnet-5-5` — 미실행

회계 식별자: `claude-sonnet-5-5::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `not_evaluated_strict_schema_incompatible`.

**미실행:** 요청·생성 응답·판정이 없습니다. Sonnet의 다른 입력에 대한 결과를 전용하거나 합성하지 않았습니다.

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "claude-sonnet-5-5::cases/answer/main-v1::b-main-06",
  "model_id": "claude-sonnet-5-5",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "claude-sonnet-5-5-2",
  "status": "not_executed",
  "fresh_result_present": false,
  "display_result_present": false,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": null,
  "latency_source": "unmeasured_no_result_row",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": false,
  "fresh_attempted": false,
  "cost": {
    "status": "not_executed",
    "cost_usd": null,
    "cost_lower_usd": null,
    "cost_upper_usd": null,
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0",
    "known_tariff_upper_subtotal_usd": "0",
    "unknown_attempts": 0,
    "bounded_attempts": 0,
    "attempts": 0
  },
  "tokens": {
    "input_known_subtotal": 0,
    "output_known_subtotal": 0,
    "input_total": null,
    "output_total": null,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "quality_evaluation_status": "not_evaluated_strict_schema_incompatible"
}
```

</details>


### 후보 `gpt-6-luna` — 성공

회계 식별자: `gpt-6-luna::cases/answer/main-v1::b-main-06`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-2.json) — `cases`에서 `b-main-06` 식별자로 찾습니다.

**최종 서비스 응답 (실제 기록):**

```json
{
  "judgments": [
    {
      "turn_id": "1",
      "key": "contribution_clarity",
      "level": 4
    },
    {
      "turn_id": "1",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 0
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "5",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 0
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 4
    }
  ]
}
```

<details>
<summary>기술 검증·오류·입력/출력 결합 기록</summary>

```json
{
  "status": "succeeded",
  "failure": null,
  "quality": "excluded_unreviewed",
  "review_status": "unreviewed"
}
```

</details>


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-51 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-51`. lifetime ID `attempt-121`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-2-raw/response-0003.json) · SHA-256 `68a4e7a1607742e03d7cdf3050fa8932090c188d961052a6fdc2a4aff85b5030`

<details>
<summary>기술 판정과 종료/잘림 표식</summary>

```json
{
  "attempt": {
    "http_status": 200,
    "task_stage": null,
    "task_schema_version": "1",
    "task_prompt_version": "report_score_v3",
    "task_stage_attempt_number": null,
    "intentional_director_review": false,
    "is_retry": false,
    "is_failed_attempt": false,
    "error_stage": null,
    "error_code": null,
    "technical_failure_cause": null,
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 7680,
    "output_tokens": 748,
    "cost_status": "bounded",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "responses",
    "finish_reasons": [],
    "response_status": "completed",
    "incomplete_reason": null,
    "truncated": false,
    "reasoning_output_tokens": 493,
    "output_tokens_observed": 748,
    "non_reasoning_output_tokens": 255,
    "visible_output_characters": 874,
    "technical_cause": "provider_reported_completion",
    "explicit_schema_request_rejection": false,
    "explicit_strict_schema_incompatibility": false
  }
}
```

</details>

**요청에서 실제 생성된 공개 텍스트/거부 필드 (잘린 문자열도 그대로):**

<details>
<summary>원본 공개 생성 필드 전체</summary>

```json
[
  {
    "source": "output[1]",
    "role": "assistant",
    "status": "completed",
    "content": [
      {
        "type": "output_text",
        "annotations": [],
        "logprobs": [],
        "text": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":0},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":1},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":2},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"8\",\"key\":\"communication\",\"level\":0},{\"turn_id\":\"9\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"9\",\"key\":\"communication\",\"level\":4}]}"
      }
    ]
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":0},{"turn_id":"2","key":"communication","level":0},{"turn_id":"3","key":"technical_reasoning","level":1},{"turn_id":"3","key":"communication","level":3},{"turn_id":"4","key":"problem_solving","level":2},{"turn_id":"4","key":"communication","level":3},{"turn_id":"5","key":"company_job_fit","level":3},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"technical_reasoning","level":2},{"turn_id":"6","key":"communication","level":3},{"turn_id":"7","key":"technical_reasoning","level":4},{"turn_id":"7","key":"communication","level":4},{"turn_id":"8","key":"communication","level":0},{"turn_id":"9","key":"technical_reasoning","level":4},{"turn_id":"9","key":"communication","level":4}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-2.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gpt-6-luna::cases/answer/main-v1::b-main-06",
  "model_id": "gpt-6-luna",
  "case_id": "b-main-06",
  "experiment": "B",
  "corpus": "cases/answer/main-v1",
  "fresh_job_id": "gpt-6-luna-2",
  "status": "succeeded",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 8098.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-51"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.00107065",
    "cost_upper_usd": "0.00125805",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.00107065",
    "known_tariff_upper_subtotal_usd": "0.00125805",
    "unknown_attempts": 0,
    "bounded_attempts": 1,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 7680,
    "output_known_subtotal": 748,
    "input_total": 7680,
    "output_total": 748,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 17,
    "strict_matches": 13,
    "acceptable_matches": 13,
    "na_mismatches": 0,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 5,
    "case_id": "b-main-06",
    "corpus": "cases/answer/main-v1",
    "predicted": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 61,
        "problem_solving": 45,
        "communication": 63,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 55
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 0,
        "technical_reasoning": 56,
        "problem_solving": 45,
        "communication": 58,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 53
    },
    "absolute_total_deviation": 2,
    "key_absolute_deviations": [
      0,
      5,
      0,
      5,
      0,
      0
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>
