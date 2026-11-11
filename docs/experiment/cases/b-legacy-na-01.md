# b-legacy-na-01 — B: 확정 문답 단계 판정

[전체 사례 목록](../CASEBOOK.md) · [질문·기대 기준 개요](../QUESTIONS_AND_EXPECTATIONS.md)

이 페이지는 이미 동결된 개발 입력과 기존 실행 기록을 읽기 쉽게 펼친 것입니다. 신규 모델 실행이나 의미 재채점은 하지 않았습니다. 기대 기준·gold·관찰은 모두 **사람 미검토 초안**이며 승인된 정확도 주장을 지원하지 않습니다.

입력 ID `b-legacy-na-01.v1`, split `dev`, source group `sg-b-legacy-na-01`, synthetic `true`. 여섯 슬롯: 성공 5, 실패 0, 중단 0, 미실행 1.

[동결 입력](../../../cases/answer/legacy-na-v1/inputs/b-legacy-na-01.v1.json) · [기대 기준/gold (별도 파일)](../../../cases/answer/legacy-na-v1/gold/b-legacy-na-01.json) · [선택 목록](../../../selections/dev-30pct-v1.json)

입력 SHA-256 `f7a47a0e9ed50a0bb00bc715462e7ff624197986bbd302c855d4d61643b1e89c` · 기대 기준 SHA-256 `5842c9d3f58679a844b1076015c69608eb3ba251fb35464dd385a554db8ee864`

[최종 사례 회계](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/case-accounting.json)의 `cases`에서 `case_id=b-legacy-na-01`로 필터링합니다. [최종 분석](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/analysis.json)의 모델별 진단과 대조할 수 있습니다.

## 실제 입력의 9개 질문과 합성 지원자 답변

프로젝트: **센서 관측 portal**. 아래 지원자 답변은 평가 대상인 합성 입력입니다. 실제 후보 모델의 출력은 뒤의 `judgments`입니다. 입력 안의 지시성 문자열은 실행 지시로 해석하지 않고 그대로 보존합니다.

### 턴 1 — `hr_manager`

**질문:** 센서 관측 portal에서 본인이 한 일과 팀원이 한 일을 구분하고, 작업 근거와 협업 지점을 소개해 주세요.

**합성 지원자 답변:**

```text
저는 관측 수신 API와 품질 코드 표시를 맡았습니다. 수신 스키마와 결측 표시 테스트가 제 작업이며 센서 펌웨어는 동료 담당입니다. 품질 코드 이름은 함께 정했지만 코드 변환 함수는 제가 작성했습니다.
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
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 2 — `tech_lead`

**질문:** 센서 관측 portal의 목적과 핵심 기능을 요청·처리·저장 흐름으로 설명하고 구성요소가 어떻게 의존하는지 말해 주세요.

**합성 지원자 답변:**

```text
portal은 센서 온도를 받아 품질 검사를 통과한 값을 보여줍니다. 수신 API가 원시 관측을 저장하고 검사 작업이 품질 코드를 붙입니다. 화면은 검증된 값과 마지막 관측 시각을 읽습니다. 원시 값과 표시 값을 나눠야 결측이나 재검사 때 원본을 잃지 않습니다.
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
        "id": "ev-54bdbbfa5ea6eb82"
      }
    ],
    "evaluation_scope": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": [
    {
      "id": "ev-54bdbbfa5ea6eb82",
      "repository_id": "repo-54bdbbfa5ea6eb82",
      "git_ref": "bd1590d725d167c7c44ecbe36bc7d6a6e2ec7e66",
      "source_type": "repository",
      "path": "docs/project-context.md",
      "metadata_key": null,
      "snippet": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.",
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

**질문:** 센서 관측 portal의 관측 시각에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
센서 관측 시각과 수신 시각 분리을 택했습니다. 선택 근거는 다음과 같습니다: 늦게 도착한 측정을 방금 측정한 온도로 표시하지 않습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 3,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "관측 시각의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "관측 시각의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 4 — `tech_lead`

**질문:** 센서 관측 portal에서 떠올릴 수 있는 구체적 문제 한 가지와 원인 확인, 수정, 검증 과정을 설명해 주세요. 검토한 대안이나 재발 방지가 있다면 함께 설명해 주세요.

**합성 지원자 답변:**

```text
결측 구간이 0도로 그려졌습니다. API JSON과 차트 입력을 비교해 null을 숫자로 바꾸는 변환에서 0이 됨을 확인했습니다. null을 유지하고 선을 끊도록 바꾼 뒤 정상 0도와 결측을 나란히 넣어 서로 다르게 보이는지 확인했습니다.
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
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 5 — `domain_lead`

**질문:** 제공된 두 JD 요구사항을 보고 센서 관측 portal에서의 본인 경험이 어떻게 대응하는지 사례로 연결해 주세요. 경험 범위의 한계도 함께 말해 주세요.

**합성 지원자 답변:**

```text
공고의 결측 구분 요구에는 제가 작성한 null 유지 변환과 0도 비교 테스트가 대응합니다. 품질 범위 요구에는 수신 시각과 관측 시각을 따로 표시한 경험이 대응합니다. 다만 센서 교정의 정확도를 검증한 것은 아니고 표시가 맞아도 센서 값 자체가 참인지 알 수는 없습니다.
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
        "id": "req-88b2293496e84a9b"
      },
      {
        "kind": "jd_requirement",
        "id": "req-6c27a6ed3057438e"
      }
    ],
    "evaluation_scope": "제공된 JD 요구사항과 개인 경험을 연결한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [
    "req-88b2293496e84a9b",
    "req-6c27a6ed3057438e"
  ],
  "evidences": []
}
```

</details>

### 턴 6 — `tech_lead`

**질문:** 센서 관측 portal의 품질 표시에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
값과 품질 코드를 함께 반환을 택했습니다. 선택 근거는 다음과 같습니다: 숫자는 있어도 의심스러운 관측임을 화면에서 구별합니다. 이상치를 조용히 삭제도 검토했습니다. 삭제는 그래프가 깨끗하지만 값이 없어진 이유를 잃습니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 6,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "품질 표시의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "품질 표시의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 7 — `tech_lead`

**질문:** 센서 관측 portal의 재검사에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
원시 관측 불변 보관을 택했습니다. 검증 규칙이 바뀌어도 같은 입력으로 표시 값을 다시 계산합니다. 비교한 보정 값으로 원본 덮기은 덮기는 공간이 적지만 이전 규칙의 영향을 되돌리기 어렵습니다. 대신 원시 값과 계산 값의 저장 공간이 함께 듭니다. 그리고 센서에서 오기 전 유실된 값은 재계산하지 못합니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 7,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "재검사의 선택과 근거를 설명한다.",
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
        "id": "doc-54bdbbfa5ea6eb82"
      }
    ],
    "evaluation_scope": "재검사의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

### 턴 8 — `domain_lead`

**질문:** 결측 관측과 실제 0도 관측이 왜 다른지 그래프를 보는 사용자에게 설명해 주세요.

**합성 지원자 답변:**

```text
결측은 측정 값이 없다는 뜻이고 0도는 실제 숫자 값입니다. 예를 들어 전원이 꺼진 센서의 구간을 0도로 그리면 온도가 내려갔다고 오해합니다. 그래서 결측은 선을 끊고 마지막 관측 시각을 함께 표시합니다.
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
        "id": "req-88b2293496e84a9b"
      },
      {
        "kind": "jd_requirement",
        "id": "req-6c27a6ed3057438e"
      }
    ],
    "evaluation_scope": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [
    "req-88b2293496e84a9b",
    "req-6c27a6ed3057438e"
  ],
  "evidences": []
}
```

</details>

### 턴 9 — `tech_lead`

**질문:** 센서 관측 portal의 구간 집계에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.

**합성 지원자 답변:**

```text
유효 관측 개수와 평균 함께 표시을 택했습니다. 선택 근거는 다음과 같습니다: 몇 개의 값으로 평균을 만들었는지 사용자가 판단합니다.
```

<details>
<summary>질문 전에 고정한 계약·연결 근거</summary>

```json
{
  "turn_no": 9,
  "persona": "tech_lead",
  "question_contract": {
    "purpose": "구간 집계의 선택과 근거를 설명한다.",
    "required_points": [
      {
        "key": "choice_reason",
        "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
      }
    ],
    "assumptions": [],
    "basis_refs": [],
    "evaluation_scope": "구간 집계의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
    "evaluation_keys": []
  },
  "analysis": null,
  "parent_turn_no": null,
  "jd_requirement_ids": [],
  "evidences": []
}
```

</details>

## 기대 판정 — 사람 미검토 draft gold

총 **30개 (turn_id, key)** 쌍입니다. 이 파일에는 대체 허용 단계 목록이 없으므로 strict/acceptable 초안 비교는 같은 단일 `level`과 대조합니다. 이것은 승인된 정답률이 아닙니다. `not_applicable`은 숫자 0과 구분합니다.

| turn_id | key | 초안 level | 초안 근거 | rubric 원문 |
|---|---|---|---|---|
| 1 | `contribution_clarity` | `4` | 센서 관측 portal: '저는 관측 수신 API와 품질 코드 표시를 맡았습니다. 수신 스키마와 결측 표시 테스트가 제 작업이며 센서 펌웨어는 동료 담당입니다. 품질 코드 이름은 함께 정했지만 코드 변환 함수는 제가 작성했습'라는 이 턴 답변에서 단독 작업, 팀원 작업과 공동 합의 경계를 모두 구분한다. | 협업 지점과 단독 기여를 명확히 구분해 설명한다. |
| 1 | `communication` | `4` | '저는 관측 수신 API와 품질 코드 표시를 맡았습니다. 수신 스키마와 결측 표시 테스트가 제 작업이며 센서 펌웨어는 동료 담당입니다. 품질 코드 이름은 함께 정했'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 2 | `project_understanding` | `4` | 센서 관측 portal: 'portal은 센서 온도를 받아 품질 검사를 통과한 값을 보여줍니다. 수신 API가 원시 관측을 저장하고 검사 작업이 품질 코드를 붙입니다. 화면은 검증된 값과 마지막 관측 시각을 읽습니다. 원시 '라는 이 턴 답변에서 구조·의존관계와 왜 그 순서나 경계를 두었는지 설명한다. | 구조·의존관계·설계 의도까지 근거를 들어 설명한다. |
| 2 | `technical_reasoning` | `not_applicable` | 질문은 프로젝트 목적과 핵심 구조 및 흐름을 설명한다.라는 범위다. technical_reasoning의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 2 | `problem_solving` | `not_applicable` | 질문은 프로젝트 목적과 핵심 구조 및 흐름을 설명한다.라는 범위다. problem_solving의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 2 | `communication` | `4` | 'portal은 센서 온도를 받아 품질 검사를 통과한 값을 보여줍니다. 수신 API가 원시 관측을 저장하고 검사 작업이 품질 코드를 붙입니다. 화면은 검증된 값과 '라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 3 | `project_understanding` | `not_applicable` | 질문은 관측 시각의 선택과 근거를 설명한다.라는 범위다. project_understanding의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 3 | `technical_reasoning` | `2` | 늦게 도착한 측정을 방금 측정한 온도로 표시하지 않습니다라는 구체 근거가 있으나 수신 시각만 저장과의 비교는 하지 않는다. | 근거는 제시하나 대안과의 비교가 없거나 피상적이다. |
| 3 | `problem_solving` | `not_applicable` | 질문은 관측 시각의 선택과 근거를 설명한다.라는 범위다. problem_solving의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 3 | `communication` | `4` | '센서 관측 시각과 수신 시각 분리을 택했습니다. 선택 근거는 다음과 같습니다: 늦게 도착한 측정을 방금 측정한 온도로 표시하지 않습니다.'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 4 | `project_understanding` | `not_applicable` | 질문은 하나의 문제를 식별하고 해결한 과정을 설명한다.라는 범위다. project_understanding의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 4 | `technical_reasoning` | `not_applicable` | 질문은 하나의 문제를 식별하고 해결한 과정을 설명한다.라는 범위다. technical_reasoning의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 4 | `problem_solving` | `3` | 센서 관측 portal: '결측 구간이 0도로 그려졌습니다. API JSON과 차트 입력을 비교해 null을 숫자로 바꾸는 변환에서 0이 됨을 확인했습니다. null을 유지하고 선을 끊도록 바꾼 뒤 정상 0도와 결측을 나란히'라는 이 턴 답변에서 관찰로 원인을 진단하고 수정 및 검증 과정을 구체적으로 설명한다. | 문제 원인을 진단하고 해결한 과정을 구체적으로 설명한다. |
| 4 | `communication` | `4` | '결측 구간이 0도로 그려졌습니다. API JSON과 차트 입력을 비교해 null을 숫자로 바꾸는 변환에서 0이 됨을 확인했습니다. null을 유지하고 선을 끊도록'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 5 | `company_job_fit` | `4` | 센서 관측 portal: '공고의 결측 구분 요구에는 제가 작성한 null 유지 변환과 0도 비교 테스트가 대응합니다. 품질 범위 요구에는 수신 시각과 관측 시각을 따로 표시한 경험이 대응합니다. 다만 센서 교정의 정확도를 '라는 이 턴 답변에서 두 요구에 대응하는 경험과 검증한 범위의 한계를 함께 설명한다. | 요구사항별로 대응하는 경험과 한계까지 균형 있게 설명한다. |
| 5 | `communication` | `4` | '공고의 결측 구분 요구에는 제가 작성한 null 유지 변환과 0도 비교 테스트가 대응합니다. 품질 범위 요구에는 수신 시각과 관측 시각을 따로 표시한 경험이 대응'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 6 | `project_understanding` | `not_applicable` | 질문은 품질 표시의 선택과 근거를 설명한다.라는 범위다. project_understanding의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 6 | `technical_reasoning` | `3` | 이상치를 조용히 삭제을 대안으로 인지하고 삭제는 그래프가 깨끗하지만 값이 없어진 이유를 잃습니다라는 차이로 선택을 설명하나 선택한 방식의 구체 비용과 한계를 함께 다루지는 않는다. | 대안을 인지하고 선택 이유를 합리적으로 설명한다. |
| 6 | `problem_solving` | `not_applicable` | 질문은 품질 표시의 선택과 근거를 설명한다.라는 범위다. problem_solving의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 6 | `communication` | `4` | '값과 품질 코드를 함께 반환을 택했습니다. 선택 근거는 다음과 같습니다: 숫자는 있어도 의심스러운 관측임을 화면에서 구별합니다. 이상치를 조용히 삭제도 검토했습니'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 7 | `project_understanding` | `not_applicable` | 질문은 재검사의 선택과 근거를 설명한다.라는 범위다. project_understanding의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 7 | `technical_reasoning` | `4` | 보정 값으로 원본 덮기과 비교하고, 선택 비용 '원시 값과 계산 값의 저장 공간이 함께 듭니다'와 한계 '센서에서 오기 전 유실된 값은 재계산하지 못합니다'까지 구체적으로 설명한다. | 트레이드오프를 구체적으로 비교하고 한계까지 인지하고 있다. |
| 7 | `problem_solving` | `not_applicable` | 질문은 재검사의 선택과 근거를 설명한다.라는 범위다. problem_solving의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 7 | `communication` | `4` | '원시 관측 불변 보관을 택했습니다. 검증 규칙이 바뀌어도 같은 입력으로 표시 값을 다시 계산합니다. 비교한 보정 값으로 원본 덮기은 덮기는 공간이 적지만 이전 규'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 8 | `company_job_fit` | `not_applicable` | 질문은 사용자에게 상태·개념의 차이를 설명하는 범위이며 JD와 본인 경험을 연결하도록 묻지 않는다. JD ID가 연결되어 있어도 직무 적합성은 관찰하지 않았다. | 원본에 별도 인용 없음 |
| 8 | `communication` | `4` | '결측은 측정 값이 없다는 뜻이고 0도는 실제 숫자 값입니다. 예를 들어 전원이 꺼진 센서의 구간을 0도로 그리면 온도가 내려갔다고 오해합니다. 그래서 결측은 선을'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |
| 9 | `project_understanding` | `not_applicable` | 질문은 구간 집계의 선택과 근거를 설명한다.라는 범위다. project_understanding의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 9 | `technical_reasoning` | `2` | 몇 개의 값으로 평균을 만들었는지 사용자가 판단합니다라는 구체 근거가 있으나 평균만 표시과의 비교는 하지 않는다. | 근거는 제시하나 대안과의 비교가 없거나 피상적이다. |
| 9 | `problem_solving` | `not_applicable` | 질문은 구간 집계의 선택과 근거를 설명한다.라는 범위다. problem_solving의 별도 설명을 요청하지 않았으므로 답변의 부족함을 0으로 만들지 않고 이 후보 key를 NA로 둔다. | 원본에 별도 인용 없음 |
| 9 | `communication` | `4` | '유효 관측 개수와 평균 함께 표시을 택했습니다. 선택 근거는 다음과 같습니다: 몇 개의 값으로 평균을 만들었는지 사용자가 판단합니다.'라는 이 턴의 표현은 선택·핵심 구분을 먼저 말하고 이유나 구체 사례를 분리해 설명한다. 기술 내용의 단계와 별도로 문장 구성을 판정한다. | 핵심을 먼저 제시하고 근거를 명확히 구조화해 설명한다. |

<details>
<summary>독립 검토 대기 항목</summary>

```json
{
  "case_id": "b-legacy-na-01",
  "version": 1,
  "review": {
    "status": "unreviewed",
    "author": "Codex",
    "reviewer": null,
    "reviewed_at": null,
    "pending_notes": [
      "전체 문답·315개 annotation은 합성 초안이다. 후보 모델 출력이나 Judge로 gold를 만든 것이 아니며 독립 사람 판정 전에는 의미 정답으로 확정하지 않는다.",
      "전 턴 evaluation_keys=[]; 8턴의 JD 링크는 F 평가 의도가 아니다.",
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
      "id": "req-88b2293496e84a9b",
      "category": "required",
      "text": "관측 값의 결측과 이상치를 구분해 설명할 수 있어야 한다."
    },
    {
      "id": "req-6c27a6ed3057438e",
      "category": "required",
      "text": "수집 지연과 품질 코드의 검증 범위를 설명해야 한다."
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
            "evidence_id": "ev-54bdbbfa5ea6eb82",
            "repository_id": "repo-54bdbbfa5ea6eb82",
            "git_ref": "bd1590d725d167c7c44ecbe36bc7d6a6e2ec7e66",
            "source_kind": "repository",
            "path": "docs/project-context.md",
            "metadata_key": null,
            "content": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.",
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
      "source_id": "doc-54bdbbfa5ea6eb82",
      "kind": "document_claim",
      "content": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.\n설계 기록: 원시 관측 불변 보관. 검증 규칙이 바뀌어도 같은 입력으로 표시 값을 다시 계산합니다",
      "location": "design-notes.md#decision-record",
      "version": "b2d0a2a0ec8ff5052000f064a223679ae55bb1d42d17e6c0b7762471dec8b792",
      "limitations": [
        "설계 기록은 구현 존재나 개인 기여를 독립 확인한 자료가 아니다."
      ],
      "title": "센서 관측 portal 설계 기록",
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
  "case_id": "b-legacy-na-01",
  "version": 1,
  "control": {
    "kind": "report",
    "split": "dev",
    "source_group_id": "sg-b-legacy-na-01",
    "synthetic": true
  },
  "payload": {
    "service_task": "report",
    "service_input": {
      "turns": [
        {
          "turn_no": 1,
          "persona": "hr_manager",
          "question": "센서 관측 portal에서 본인이 한 일과 팀원이 한 일을 구분하고, 작업 근거와 협업 지점을 소개해 주세요.",
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
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "저는 관측 수신 API와 품질 코드 표시를 맡았습니다. 수신 스키마와 결측 표시 테스트가 제 작업이며 센서 펌웨어는 동료 담당입니다. 품질 코드 이름은 함께 정했지만 코드 변환 함수는 제가 작성했습니다."
        },
        {
          "turn_no": 2,
          "persona": "tech_lead",
          "question": "센서 관측 portal의 목적과 핵심 기능을 요청·처리·저장 흐름으로 설명하고 구성요소가 어떻게 의존하는지 말해 주세요.",
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
                "id": "ev-54bdbbfa5ea6eb82"
              }
            ],
            "evaluation_scope": "프로젝트 목적과 핵심 구조 및 흐름을 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [
            {
              "id": "ev-54bdbbfa5ea6eb82",
              "repository_id": "repo-54bdbbfa5ea6eb82",
              "git_ref": "bd1590d725d167c7c44ecbe36bc7d6a6e2ec7e66",
              "source_type": "repository",
              "path": "docs/project-context.md",
              "metadata_key": null,
              "snippet": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.",
              "tool_name": "repository_reader",
              "summary": "제공된 프로젝트 설명의 제한된 구간",
              "start_line": 1,
              "end_line": 1
            }
          ],
          "answer": "portal은 센서 온도를 받아 품질 검사를 통과한 값을 보여줍니다. 수신 API가 원시 관측을 저장하고 검사 작업이 품질 코드를 붙입니다. 화면은 검증된 값과 마지막 관측 시각을 읽습니다. 원시 값과 표시 값을 나눠야 결측이나 재검사 때 원본을 잃지 않습니다."
        },
        {
          "turn_no": 3,
          "persona": "tech_lead",
          "question": "센서 관측 portal의 관측 시각에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "관측 시각의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "관측 시각의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "센서 관측 시각과 수신 시각 분리을 택했습니다. 선택 근거는 다음과 같습니다: 늦게 도착한 측정을 방금 측정한 온도로 표시하지 않습니다."
        },
        {
          "turn_no": 4,
          "persona": "tech_lead",
          "question": "센서 관측 portal에서 떠올릴 수 있는 구체적 문제 한 가지와 원인 확인, 수정, 검증 과정을 설명해 주세요. 검토한 대안이나 재발 방지가 있다면 함께 설명해 주세요.",
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
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "결측 구간이 0도로 그려졌습니다. API JSON과 차트 입력을 비교해 null을 숫자로 바꾸는 변환에서 0이 됨을 확인했습니다. null을 유지하고 선을 끊도록 바꾼 뒤 정상 0도와 결측을 나란히 넣어 서로 다르게 보이는지 확인했습니다."
        },
        {
          "turn_no": 5,
          "persona": "domain_lead",
          "question": "제공된 두 JD 요구사항을 보고 센서 관측 portal에서의 본인 경험이 어떻게 대응하는지 사례로 연결해 주세요. 경험 범위의 한계도 함께 말해 주세요.",
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
                "id": "req-88b2293496e84a9b"
              },
              {
                "kind": "jd_requirement",
                "id": "req-6c27a6ed3057438e"
              }
            ],
            "evaluation_scope": "제공된 JD 요구사항과 개인 경험을 연결한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [
            "req-88b2293496e84a9b",
            "req-6c27a6ed3057438e"
          ],
          "evidences": [],
          "answer": "공고의 결측 구분 요구에는 제가 작성한 null 유지 변환과 0도 비교 테스트가 대응합니다. 품질 범위 요구에는 수신 시각과 관측 시각을 따로 표시한 경험이 대응합니다. 다만 센서 교정의 정확도를 검증한 것은 아니고 표시가 맞아도 센서 값 자체가 참인지 알 수는 없습니다."
        },
        {
          "turn_no": 6,
          "persona": "tech_lead",
          "question": "센서 관측 portal의 품질 표시에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "품질 표시의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "품질 표시의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "값과 품질 코드를 함께 반환을 택했습니다. 선택 근거는 다음과 같습니다: 숫자는 있어도 의심스러운 관측임을 화면에서 구별합니다. 이상치를 조용히 삭제도 검토했습니다. 삭제는 그래프가 깨끗하지만 값이 없어진 이유를 잃습니다."
        },
        {
          "turn_no": 7,
          "persona": "tech_lead",
          "question": "센서 관측 portal의 재검사에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "재검사의 선택과 근거를 설명한다.",
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
                "id": "doc-54bdbbfa5ea6eb82"
              }
            ],
            "evaluation_scope": "재검사의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "원시 관측 불변 보관을 택했습니다. 검증 규칙이 바뀌어도 같은 입력으로 표시 값을 다시 계산합니다. 비교한 보정 값으로 원본 덮기은 덮기는 공간이 적지만 이전 규칙의 영향을 되돌리기 어렵습니다. 대신 원시 값과 계산 값의 저장 공간이 함께 듭니다. 그리고 센서에서 오기 전 유실된 값은 재계산하지 못합니다."
        },
        {
          "turn_no": 8,
          "persona": "domain_lead",
          "question": "결측 관측과 실제 0도 관측이 왜 다른지 그래프를 보는 사용자에게 설명해 주세요.",
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
                "id": "req-88b2293496e84a9b"
              },
              {
                "kind": "jd_requirement",
                "id": "req-6c27a6ed3057438e"
              }
            ],
            "evaluation_scope": "프로젝트의 사용자 관점에서 상태 또는 개념의 차이를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [
            "req-88b2293496e84a9b",
            "req-6c27a6ed3057438e"
          ],
          "evidences": [],
          "answer": "결측은 측정 값이 없다는 뜻이고 0도는 실제 숫자 값입니다. 예를 들어 전원이 꺼진 센서의 구간을 0도로 그리면 온도가 내려갔다고 오해합니다. 그래서 결측은 선을 끊고 마지막 관측 시각을 함께 표시합니다."
        },
        {
          "turn_no": 9,
          "persona": "tech_lead",
          "question": "센서 관측 portal의 구간 집계에서 어떤 방식을 택했고 주된 이유는 무엇인가요? 비교한 대안이나 남는 한계가 있다면 설명해 주세요.",
          "question_contract": {
            "purpose": "구간 집계의 선택과 근거를 설명한다.",
            "required_points": [
              {
                "key": "choice_reason",
                "description": "선택한 방식과 해당 상황에서의 이유를 설명한다."
              }
            ],
            "assumptions": [],
            "basis_refs": [],
            "evaluation_scope": "구간 집계의 선택과 근거를 설명한다. 답변의 의도 적합성과 설명 구성을 함께 확인한다.",
            "evaluation_keys": []
          },
          "analysis": null,
          "parent_turn_no": null,
          "jd_requirement_ids": [],
          "evidences": [],
          "answer": "유효 관측 개수와 평균 함께 표시을 택했습니다. 선택 근거는 다음과 같습니다: 몇 개의 값으로 평균을 만들었는지 사용자가 판단합니다."
        }
      ],
      "requirements": [
        {
          "id": "req-88b2293496e84a9b",
          "category": "required",
          "text": "관측 값의 결측과 이상치를 구분해 설명할 수 있어야 한다."
        },
        {
          "id": "req-6c27a6ed3057438e",
          "category": "required",
          "text": "수집 지연과 품질 코드의 검증 범위를 설명해야 한다."
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
                "evidence_id": "ev-54bdbbfa5ea6eb82",
                "repository_id": "repo-54bdbbfa5ea6eb82",
                "git_ref": "bd1590d725d167c7c44ecbe36bc7d6a6e2ec7e66",
                "source_kind": "repository",
                "path": "docs/project-context.md",
                "metadata_key": null,
                "content": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.",
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
          "source_id": "doc-54bdbbfa5ea6eb82",
          "kind": "document_claim",
          "content": "온도 센서의 원시 관측과 검증 후 표시 값을 구분하는 portal이다. 센서 시각·수신 시각·품질 코드를 보관하며 결측을 0도로 대체하지 않는다.\n설계 기록: 원시 관측 불변 보관. 검증 규칙이 바뀌어도 같은 입력으로 표시 값을 다시 계산합니다",
          "location": "design-notes.md#decision-record",
          "version": "b2d0a2a0ec8ff5052000f064a223679ae55bb1d42d17e6c0b7762471dec8b792",
          "limitations": [
            "설계 기록은 구현 존재나 개인 기여를 독립 확인한 자료가 아니다."
          ],
          "title": "센서 관측 portal 설계 기록",
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
| `claude-haiku-5-5` | **성공** (`succeeded`) | 1 | 있음 | 기록된 실패 없음 |
| `claude-sonnet-5-5` | **미실행** (`not_executed`) | 0 | 없음 | 기록된 실패 없음 |
| `gpt-6-luna` | **성공** (`succeeded`) | 2 | 있음 | output_truncated_at_token_limit |


### 각 (턴, key)의 초안 gold와 실제 단계

표의 `—`는 미실행/유효한 최종 판정 없음이며 0점이 아닙니다. 별도 실패 요청의 부분 텍스트는 판정값으로 보충하지 않았습니다.

| 턴 / key | draft gold | `gpt-6.1-sol` | `gemini-3.8-flash` | `gemini-4-argon` | `claude-haiku-5-5` | `claude-sonnet-5-5` | `gpt-6-luna` |
|---|---|---|---|---|---|---|---|
| 1 / `contribution_clarity` | `4` | `4` | `4` | `4` | `4` | — | `4` |
| 1 / `communication` | `4` | `4` | `4` | `4` | `3` ≠ | — | `4` |
| 2 / `project_understanding` | `4` | `4` | `4` | `4` | `4` | — | `4` |
| 2 / `technical_reasoning` | `not_applicable` | `2` ≠ | `not_applicable` | `not_applicable` | `2` ≠ | — | `4` ≠ |
| 2 / `problem_solving` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | — | `not_applicable` |
| 2 / `communication` | `4` | `4` | `3` ≠ | `4` | `3` ≠ | — | `3` ≠ |
| 3 / `project_understanding` | `not_applicable` | `3` ≠ | `not_applicable` | `not_applicable` | `2` ≠ | — | `2` ≠ |
| 3 / `technical_reasoning` | `2` | `2` | `2` | `2` | `1` ≠ | — | `2` |
| 3 / `problem_solving` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | — | `not_applicable` |
| 3 / `communication` | `4` | `4` | `3` ≠ | `3` ≠ | `1` ≠ | — | `3` ≠ |
| 4 / `project_understanding` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `3` ≠ | — | `2` ≠ |
| 4 / `technical_reasoning` | `not_applicable` | `2` ≠ | `not_applicable` | `not_applicable` | `2` ≠ | — | `3` ≠ |
| 4 / `problem_solving` | `3` | `3` | `3` | `3` | `3` | — | `3` |
| 4 / `communication` | `4` | `4` | `3` ≠ | `3` ≠ | `3` ≠ | — | `3` ≠ |
| 5 / `company_job_fit` | `4` | `4` | `4` | `4` | `4` | — | `3` ≠ |
| 5 / `communication` | `4` | `4` | `4` | `4` | `3` ≠ | — | `4` |
| 6 / `project_understanding` | `not_applicable` | `3` ≠ | `not_applicable` | `not_applicable` | `2` ≠ | — | `2` ≠ |
| 6 / `technical_reasoning` | `3` | `3` | `3` | `3` | `3` | — | `4` ≠ |
| 6 / `problem_solving` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | — | `not_applicable` |
| 6 / `communication` | `4` | `4` | `3` ≠ | `3` ≠ | `2` ≠ | — | `3` ≠ |
| 7 / `project_understanding` | `not_applicable` | `4` ≠ | `not_applicable` | `not_applicable` | `3` ≠ | — | `2` ≠ |
| 7 / `technical_reasoning` | `4` | `4` | `4` | `4` | `4` | — | `4` |
| 7 / `problem_solving` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | — | `not_applicable` |
| 7 / `communication` | `4` | `4` | `3` ≠ | `4` | `3` ≠ | — | `3` ≠ |
| 8 / `company_job_fit` | `not_applicable` | `not_applicable` | `3` ≠ | `not_applicable` | `2` ≠ | — | `not_applicable` |
| 8 / `communication` | `4` | `4` | `4` | `4` | `3` ≠ | — | `4` |
| 9 / `project_understanding` | `not_applicable` | `3` ≠ | `not_applicable` | `not_applicable` | `1` ≠ | — | `2` ≠ |
| 9 / `technical_reasoning` | `2` | `2` | `2` | `2` | `1` ≠ | — | `2` |
| 9 / `problem_solving` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | `not_applicable` | — | `not_applicable` |
| 9 / `communication` | `4` | `4` | `3` ≠ | `3` ≠ | `2` ≠ | — | `3` ≠ |


### 초안과의 기계적 비교 — 승인된 정확도 아님

| 후보 슬롯 | strict = acceptable 초안 일치 | 수치 단계 MAE | 코드 환산 total (후보 / draft) |
|---|---|---|---|
| `gpt-6.1-sol` | 24/30 | 0 | 79 / 82 |
| `gemini-3.8-flash` | 23/30 | 0.352941 | 78 / 82 |
| `gemini-4-argon` | 26/30 | 0.235294 | 81 / 82 |
| `claude-haiku-5-5` | 11/30 | 0.882353 | 65 / 82 |
| `claude-sonnet-5-5` | 비교 불가 (미실행) | — | — |
| `gpt-6-luna` | 15/30 | 0.470588 | 72 / 82 |


MAE는 양쪽 값이 숫자인 쌍만 사용합니다. `not_applicable` 불일치는 위 쌍별 표에 남으며 숫자 MAE에서 빠집니다. total은 모델이 출력한 점수가 아니라 원본 final-analysis의 코드 환산 진단 값입니다.


### 후보 `gpt-6.1-sol` — 성공

회계 식별자: `gpt-6.1-sol::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-3.json) — `cases`에서 `b-legacy-na-01` 식별자로 찾습니다.

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
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": 3
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "communication",
      "level": 4
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
      "key": "project_understanding",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": "not_applicable"
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": 3
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
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


#### 요청 elice-dev30-10usd-20261111-recovery-2::attempt-27 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-2::attempt-27`. lifetime ID `attempt-29`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-3-raw/response-0001.json) · SHA-256 `4ea11d84a2930b6d5b98d63076b60e1fbc944e11336a305e133ddbf69220fb56`

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
    "input_tokens": 7975,
    "output_tokens": 947,
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
    "reasoning_output_tokens": 483,
    "output_tokens_observed": 947,
    "non_reasoning_output_tokens": 464,
    "visible_output_characters": 1667,
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
        "text": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"2\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"3\",\"key\":\"project_understanding\",\"level\":3},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"3\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"4\",\"key\":\"project_understanding\",\"level\":\"not_applicable\"},{\"turn_id\":\"4\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":4},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"project_understanding\",\"level\":3},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":3},{\"turn_id\":\"6\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"project_understanding\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"7\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"8\",\"key\":\"company_job_fit\",\"level\":\"not_applicable\"},{\"turn_id\":\"8\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"9\",\"key\":\"project_understanding\",\"level\":3},{\"turn_id\":\"9\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"9\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"9\",\"key\":\"communication\",\"level\":4}]}"
      }
    ]
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":4},{"turn_id":"2","key":"technical_reasoning","level":2},{"turn_id":"2","key":"problem_solving","level":"not_applicable"},{"turn_id":"2","key":"communication","level":4},{"turn_id":"3","key":"project_understanding","level":3},{"turn_id":"3","key":"technical_reasoning","level":2},{"turn_id":"3","key":"problem_solving","level":"not_applicable"},{"turn_id":"3","key":"communication","level":4},{"turn_id":"4","key":"project_understanding","level":"not_applicable"},{"turn_id":"4","key":"technical_reasoning","level":2},{"turn_id":"4","key":"problem_solving","level":3},{"turn_id":"4","key":"communication","level":4},{"turn_id":"5","key":"company_job_fit","level":4},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"project_understanding","level":3},{"turn_id":"6","key":"technical_reasoning","level":3},{"turn_id":"6","key":"problem_solving","level":"not_applicable"},{"turn_id":"6","key":"communication","level":4},{"turn_id":"7","key":"project_understanding","level":4},{"turn_id":"7","key":"technical_reasoning","level":4},{"turn_id":"7","key":"problem_solving","level":"not_applicable"},{"turn_id":"7","key":"communication","level":4},{"turn_id":"8","key":"company_job_fit","level":"not_applicable"},{"turn_id":"8","key":"communication","level":4},{"turn_id":"9","key":"project_understanding","level":3},{"turn_id":"9","key":"technical_reasoning","level":2},{"turn_id":"9","key":"problem_solving","level":"not_applicable"},{"turn_id":"9","key":"communication","level":4}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-2/results/gpt-6.1-sol-3.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gpt-6.1-sol::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "gpt-6.1-sol",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "gpt-6.1-sol-3",
  "status": "succeeded",
  "fresh_result_present": false,
  "display_result_present": true,
  "result_reused": true,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-2",
  "reused_output_sha256": "1ef15a3837c1488b2bc5ad4d9127d4dfb58659b9a23332a5d0101f1ee528465f",
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 20635.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-2::attempt-27"
  ],
  "fresh_attempt_ids": [],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": false,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.0242984",
    "cost_upper_usd": "0.0244858",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.0242984",
    "known_tariff_upper_subtotal_usd": "0.0244858",
    "unknown_attempts": 0,
    "bounded_attempts": 1,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 7975,
    "output_known_subtotal": 947,
    "input_total": 7975,
    "output_total": 947,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 30,
    "strict_matches": 24,
    "acceptable_matches": 24,
    "na_mismatches": 6,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 0,
    "case_id": "b-legacy-na-01",
    "corpus": "cases/answer/legacy-na-v1",
    "predicted": {
      "keys": {
        "project_understanding": 78,
        "technical_reasoning": 57,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 79
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 82
    },
    "absolute_total_deviation": 3,
    "key_absolute_deviations": [
      12,
      6,
      0,
      0,
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

회계 식별자: `gemini-3.8-flash::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-3.json) — `cases`에서 `b-legacy-na-01` 식별자로 찾습니다.

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
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
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
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 3
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


#### 요청 elice-dev30-10usd-20261111-recovery-3::attempt-19 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-3::attempt-19`. lifetime ID `attempt-49`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-3-raw/response-0001.json) · SHA-256 `ab23534c796652081368cca16cb078812e7b04fa2b670ee85e979d5f56fd7b00`

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
    "input_tokens": 6678,
    "output_tokens": 1032,
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
    "output_tokens_observed": 1032,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 2770,
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
    "content": "{\n  \"judgments\": [\n    {\n      \"turn_id\": \"1\",\n      \"key\": \"contribution_clarity\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"1\",\n      \"key\": \"communication\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"project_understanding\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"technical_reasoning\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"problem_solving\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"2\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"project_understanding\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 2\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"problem_solving\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"3\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"project_understanding\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"technical_reasoning\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"problem_solving\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"4\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"5\",\n      \"key\": \"company_job_fit\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"5\",\n      \"key\": \"communication\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"project_understanding\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"problem_solving\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"6\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"project_understanding\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"problem_solving\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"7\",\n      \"key\": \"communication\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"8\",\n      \"key\": \"company_job_fit\",\n      \"level\": 3\n    },\n    {\n      \"turn_id\": \"8\",\n      \"key\": \"communication\",\n      \"level\": 4\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"project_understanding\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"technical_reasoning\",\n      \"level\": 2\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"problem_solving\",\n      \"level\": \"not_applicable\"\n    },\n    {\n      \"turn_id\": \"9\",\n      \"key\": \"communication\",\n      \"level\": 3\n    }\n  ]\n}",
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
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
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
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 3
    }
  ]
}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-3/results/gemini-3.8-flash-3.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gemini-3.8-flash::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "gemini-3.8-flash",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "gemini-3.8-flash-3",
  "status": "succeeded",
  "fresh_result_present": false,
  "display_result_present": true,
  "result_reused": true,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-3",
  "reused_output_sha256": "bce897786bbefde536a7b0ce28a399f4c329792a98ff882971107b01aaea8b0c",
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 7474.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-3::attempt-19"
  ],
  "fresh_attempt_ids": [],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": false,
  "cost": {
    "status": "confirmed",
    "cost_usd": "0.0088785",
    "cost_lower_usd": "0.0088785",
    "cost_upper_usd": "0.0088785",
    "known_confirmed_subtotal_usd": "0.0088785",
    "known_tariff_lower_subtotal_usd": "0.0088785",
    "known_tariff_upper_subtotal_usd": "0.0088785",
    "unknown_attempts": 0,
    "bounded_attempts": 0,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 6678,
    "output_known_subtotal": 1032,
    "input_total": 6678,
    "output_total": 1032,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 30,
    "strict_matches": 23,
    "acceptable_matches": 23,
    "na_mismatches": 1,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 6,
    "case_id": "b-legacy-na-01",
    "corpus": "cases/answer/legacy-na-v1",
    "predicted": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 77,
        "contribution_clarity": 90,
        "company_job_fit": 80
      },
      "total": 78
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 82
    },
    "absolute_total_deviation": 4,
    "key_absolute_deviations": [
      0,
      0,
      0,
      13,
      0,
      10
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `gemini-4-argon` — 성공

회계 식별자: `gemini-4-argon::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-3.json) — `cases`에서 `b-legacy-na-01` 식별자로 찾습니다.

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
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": "not_applicable"
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
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
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": "not_applicable"
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 3
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


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-5 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-5`. lifetime ID `attempt-75`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-3-raw/response-0001.json) · SHA-256 `0266660389b84426c556f41bdc58cbbeb128fe4893d7d03c2312fcf23395805d`

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
    "input_tokens": 6644,
    "output_tokens": 692,
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
    "output_tokens_observed": 692,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 1937,
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
    "content": "{\"judgments\": [{\"turn_id\": \"1\", \"key\": \"contribution_clarity\", \"level\": 4}, {\"turn_id\": \"1\", \"key\": \"communication\", \"level\": 4}, {\"turn_id\": \"2\", \"key\": \"project_understanding\", \"level\": 4}, {\"turn_id\": \"2\", \"key\": \"technical_reasoning\", \"level\": \"not_applicable\"}, {\"turn_id\": \"2\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"2\", \"key\": \"communication\", \"level\": 4}, {\"turn_id\": \"3\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"3\", \"key\": \"technical_reasoning\", \"level\": 2}, {\"turn_id\": \"3\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"3\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"4\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"4\", \"key\": \"technical_reasoning\", \"level\": \"not_applicable\"}, {\"turn_id\": \"4\", \"key\": \"problem_solving\", \"level\": 3}, {\"turn_id\": \"4\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"5\", \"key\": \"company_job_fit\", \"level\": 4}, {\"turn_id\": \"5\", \"key\": \"communication\", \"level\": 4}, {\"turn_id\": \"6\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"6\", \"key\": \"technical_reasoning\", \"level\": 3}, {\"turn_id\": \"6\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"6\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"7\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"7\", \"key\": \"technical_reasoning\", \"level\": 4}, {\"turn_id\": \"7\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"7\", \"key\": \"communication\", \"level\": 4}, {\"turn_id\": \"8\", \"key\": \"company_job_fit\", \"level\": \"not_applicable\"}, {\"turn_id\": \"8\", \"key\": \"communication\", \"level\": 4}, {\"turn_id\": \"9\", \"key\": \"project_understanding\", \"level\": \"not_applicable\"}, {\"turn_id\": \"9\", \"key\": \"technical_reasoning\", \"level\": 2}, {\"turn_id\": \"9\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"9\", \"key\": \"communication\", \"level\": 3}]}",
    "refusal": null
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments": [{"turn_id": "1", "key": "contribution_clarity", "level": 4}, {"turn_id": "1", "key": "communication", "level": 4}, {"turn_id": "2", "key": "project_understanding", "level": 4}, {"turn_id": "2", "key": "technical_reasoning", "level": "not_applicable"}, {"turn_id": "2", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "2", "key": "communication", "level": 4}, {"turn_id": "3", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "3", "key": "technical_reasoning", "level": 2}, {"turn_id": "3", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "3", "key": "communication", "level": 3}, {"turn_id": "4", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "4", "key": "technical_reasoning", "level": "not_applicable"}, {"turn_id": "4", "key": "problem_solving", "level": 3}, {"turn_id": "4", "key": "communication", "level": 3}, {"turn_id": "5", "key": "company_job_fit", "level": 4}, {"turn_id": "5", "key": "communication", "level": 4}, {"turn_id": "6", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "6", "key": "technical_reasoning", "level": 3}, {"turn_id": "6", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "6", "key": "communication", "level": 3}, {"turn_id": "7", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "7", "key": "technical_reasoning", "level": 4}, {"turn_id": "7", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "7", "key": "communication", "level": 4}, {"turn_id": "8", "key": "company_job_fit", "level": "not_applicable"}, {"turn_id": "8", "key": "communication", "level": 4}, {"turn_id": "9", "key": "project_understanding", "level": "not_applicable"}, {"turn_id": "9", "key": "technical_reasoning", "level": 2}, {"turn_id": "9", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "9", "key": "communication", "level": 3}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gemini-4-argon-3.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gemini-4-argon::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "gemini-4-argon",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "gemini-4-argon-3",
  "status": "succeeded",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 17615.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-5"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "confirmed",
    "cost_usd": "0.020208",
    "cost_lower_usd": "0.020208",
    "cost_upper_usd": "0.020208",
    "known_confirmed_subtotal_usd": "0.020208",
    "known_tariff_lower_subtotal_usd": "0.020208",
    "known_tariff_upper_subtotal_usd": "0.020208",
    "unknown_attempts": 0,
    "bounded_attempts": 0,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 6644,
    "output_known_subtotal": 692,
    "input_total": 6644,
    "output_total": 692,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 30,
    "strict_matches": 26,
    "acceptable_matches": 26,
    "na_mismatches": 0,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 4,
    "case_id": "b-legacy-na-01",
    "corpus": "cases/answer/legacy-na-v1",
    "predicted": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 81,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 81
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 82
    },
    "absolute_total_deviation": 1,
    "key_absolute_deviations": [
      0,
      0,
      0,
      9,
      0,
      0
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `claude-haiku-5-5` — 성공

회계 식별자: `claude-haiku-5-5::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-3.json) — `cases`에서 `b-legacy-na-01` 식별자로 찾습니다.

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
      "level": 3
    },
    {
      "turn_id": "2",
      "key": "project_understanding",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 1
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
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
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 2
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": 2
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": 1
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 1
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 2
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


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-27 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-27`. lifetime ID `attempt-97`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-3-raw/response-0001.json) · SHA-256 `9a1c549fce0e119f0cd740434d722e6f19ac74b010a898d74ce22bae2dfb670a`

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
    "input_tokens": 13628,
    "output_tokens": 744,
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
    "output_tokens_observed": 744,
    "non_reasoning_output_tokens": null,
    "visible_output_characters": 1817,
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
    "content": "{\"judgments\": [{\"turn_id\": \"1\", \"key\": \"contribution_clarity\", \"level\": 4}, {\"turn_id\": \"1\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"2\", \"key\": \"project_understanding\", \"level\": 4}, {\"turn_id\": \"2\", \"key\": \"technical_reasoning\", \"level\": 2}, {\"turn_id\": \"2\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"2\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"3\", \"key\": \"project_understanding\", \"level\": 2}, {\"turn_id\": \"3\", \"key\": \"technical_reasoning\", \"level\": 1}, {\"turn_id\": \"3\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"3\", \"key\": \"communication\", \"level\": 1}, {\"turn_id\": \"4\", \"key\": \"project_understanding\", \"level\": 3}, {\"turn_id\": \"4\", \"key\": \"technical_reasoning\", \"level\": 2}, {\"turn_id\": \"4\", \"key\": \"problem_solving\", \"level\": 3}, {\"turn_id\": \"4\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"5\", \"key\": \"company_job_fit\", \"level\": 4}, {\"turn_id\": \"5\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"6\", \"key\": \"project_understanding\", \"level\": 2}, {\"turn_id\": \"6\", \"key\": \"technical_reasoning\", \"level\": 3}, {\"turn_id\": \"6\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"6\", \"key\": \"communication\", \"level\": 2}, {\"turn_id\": \"7\", \"key\": \"project_understanding\", \"level\": 3}, {\"turn_id\": \"7\", \"key\": \"technical_reasoning\", \"level\": 4}, {\"turn_id\": \"7\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"7\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"8\", \"key\": \"company_job_fit\", \"level\": 2}, {\"turn_id\": \"8\", \"key\": \"communication\", \"level\": 3}, {\"turn_id\": \"9\", \"key\": \"project_understanding\", \"level\": 1}, {\"turn_id\": \"9\", \"key\": \"technical_reasoning\", \"level\": 1}, {\"turn_id\": \"9\", \"key\": \"problem_solving\", \"level\": \"not_applicable\"}, {\"turn_id\": \"9\", \"key\": \"communication\", \"level\": 2}]}",
    "refusal": null
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments": [{"turn_id": "1", "key": "contribution_clarity", "level": 4}, {"turn_id": "1", "key": "communication", "level": 3}, {"turn_id": "2", "key": "project_understanding", "level": 4}, {"turn_id": "2", "key": "technical_reasoning", "level": 2}, {"turn_id": "2", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "2", "key": "communication", "level": 3}, {"turn_id": "3", "key": "project_understanding", "level": 2}, {"turn_id": "3", "key": "technical_reasoning", "level": 1}, {"turn_id": "3", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "3", "key": "communication", "level": 1}, {"turn_id": "4", "key": "project_understanding", "level": 3}, {"turn_id": "4", "key": "technical_reasoning", "level": 2}, {"turn_id": "4", "key": "problem_solving", "level": 3}, {"turn_id": "4", "key": "communication", "level": 3}, {"turn_id": "5", "key": "company_job_fit", "level": 4}, {"turn_id": "5", "key": "communication", "level": 3}, {"turn_id": "6", "key": "project_understanding", "level": 2}, {"turn_id": "6", "key": "technical_reasoning", "level": 3}, {"turn_id": "6", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "6", "key": "communication", "level": 2}, {"turn_id": "7", "key": "project_understanding", "level": 3}, {"turn_id": "7", "key": "technical_reasoning", "level": 4}, {"turn_id": "7", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "7", "key": "communication", "level": 3}, {"turn_id": "8", "key": "company_job_fit", "level": 2}, {"turn_id": "8", "key": "communication", "level": 3}, {"turn_id": "9", "key": "project_understanding", "level": 1}, {"turn_id": "9", "key": "technical_reasoning", "level": 1}, {"turn_id": "9", "key": "problem_solving", "level": "not_applicable"}, {"turn_id": "9", "key": "communication", "level": 2}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/claude-haiku-5-5-3.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "claude-haiku-5-5::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "claude-haiku-5-5",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "claude-haiku-5-5-3",
  "status": "succeeded",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 2964.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-27"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.0013717",
    "cost_upper_usd": "0.0027345",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.0013717",
    "known_tariff_upper_subtotal_usd": "0.0027345",
    "unknown_attempts": 0,
    "bounded_attempts": 1,
    "attempts": 1
  },
  "tokens": {
    "input_known_subtotal": 13628,
    "output_known_subtotal": 744,
    "input_total": 13628,
    "output_total": 744,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 30,
    "strict_matches": 11,
    "acceptable_matches": 11,
    "na_mismatches": 8,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 15,
    "case_id": "b-legacy-na-01",
    "corpus": "cases/answer/legacy-na-v1",
    "predicted": {
      "keys": {
        "project_understanding": 57,
        "technical_reasoning": 48,
        "problem_solving": 70,
        "communication": 59,
        "contribution_clarity": 90,
        "company_job_fit": 68
      },
      "total": 65
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 82
    },
    "absolute_total_deviation": 17,
    "key_absolute_deviations": [
      33,
      15,
      0,
      31,
      0,
      22
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>


### 후보 `claude-sonnet-5-5` — 미실행

회계 식별자: `claude-sonnet-5-5::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `not_evaluated_strict_schema_incompatible`.

**미실행:** 요청·생성 응답·판정이 없습니다. Sonnet의 다른 입력에 대한 결과를 전용하거나 합성하지 않았습니다.

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "claude-sonnet-5-5::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "claude-sonnet-5-5",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "claude-sonnet-5-5-3",
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

회계 식별자: `gpt-6-luna::cases/answer/legacy-na-v1::b-legacy-na-01`. review 상태 `unreviewed`, 의미 평가 상태 `unreviewed_draft_diagnostic_only`.

[원래 결과 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-3.json) — `cases`에서 `b-legacy-na-01` 식별자로 찾습니다.

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
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "2",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "2",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "3",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "3",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "3",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "4",
      "key": "technical_reasoning",
      "level": 3
    },
    {
      "turn_id": "4",
      "key": "problem_solving",
      "level": 3
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
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "6",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "6",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "6",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "7",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "7",
      "key": "technical_reasoning",
      "level": 4
    },
    {
      "turn_id": "7",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "7",
      "key": "communication",
      "level": 3
    },
    {
      "turn_id": "8",
      "key": "company_job_fit",
      "level": "not_applicable"
    },
    {
      "turn_id": "8",
      "key": "communication",
      "level": 4
    },
    {
      "turn_id": "9",
      "key": "project_understanding",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "technical_reasoning",
      "level": 2
    },
    {
      "turn_id": "9",
      "key": "problem_solving",
      "level": "not_applicable"
    },
    {
      "turn_id": "9",
      "key": "communication",
      "level": 3
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


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-53 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-53`. lifetime ID `attempt-123`, SDK 시도 `1`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-3-raw/response-0001.json) · SHA-256 `50de4c89ee8360fe0ef8a69cbd261d072429f5d9bace771eb30bbf0b6226b798`

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
    "error_stage": "provider",
    "error_code": "llm_failed",
    "technical_failure_cause": "output_truncated_at_token_limit",
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 7975,
    "output_tokens": 2000,
    "cost_status": "bounded",
    "unknown_reason": null,
    "identity_inference": null
  },
  "raw_diagnostics": {
    "protocol": "responses",
    "finish_reasons": [],
    "response_status": "incomplete",
    "incomplete_reason": "max_output_tokens",
    "truncated": true,
    "reasoning_output_tokens": 1642,
    "output_tokens_observed": 2000,
    "non_reasoning_output_tokens": 358,
    "visible_output_characters": 1283,
    "technical_cause": "output_truncated_at_token_limit",
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
    "source": "output[4]",
    "role": "assistant",
    "status": "incomplete",
    "content": [
      {
        "type": "output_text",
        "annotations": [],
        "logprobs": [],
        "text": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"2\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"3\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"3\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"project_understanding\",\"level\":\"not_applicable\"},{\"turn_id\":\"4\",\"key\":\"technical_reasoning\",\"level\":\"not_applicable\"},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":4},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"problem_solving\",\"level\":\"not"
      }
    ]
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":4},{"turn_id":"2","key":"technical_reasoning","level":2},{"turn_id":"2","key":"problem_solving","level":"not_applicable"},{"turn_id":"2","key":"communication","level":4},{"turn_id":"3","key":"project_understanding","level":2},{"turn_id":"3","key":"technical_reasoning","level":2},{"turn_id":"3","key":"problem_solving","level":"not_applicable"},{"turn_id":"3","key":"communication","level":3},{"turn_id":"4","key":"project_understanding","level":"not_applicable"},{"turn_id":"4","key":"technical_reasoning","level":"not_applicable"},{"turn_id":"4","key":"problem_solving","level":3},{"turn_id":"4","key":"communication","level":3},{"turn_id":"5","key":"company_job_fit","level":4},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"project_understanding","level":2},{"turn_id":"6","key":"technical_reasoning","level":4},{"turn_id":"6","key":"problem_solving","level":"not_applicable"},{"turn_id":"6","key":"communication","level":4},{"turn_id":"7","key":"project_understanding","level":2},{"turn_id":"7","key":"technical_reasoning","level":4},{"turn_id":"7","key":"problem_solving","level":"not
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-3.json)


#### 요청 elice-dev30-10usd-20261111-recovery-4::attempt-54 — 단계 기록 없음

전체 물리 ID: `C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-54`. lifetime ID `attempt-124`, SDK 시도 `2`.

[원본 provider 응답 JSON](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-3-raw/response-0002.json) · SHA-256 `b7e859d256707fca61eb21326297b43c954cf50534927ac47769b5519c87b710`

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
    "is_retry": true,
    "is_failed_attempt": false,
    "error_stage": null,
    "error_code": null,
    "technical_failure_cause": null,
    "provider_error_or_timeout_proven": null,
    "origin_case_status": "succeeded",
    "input_tokens": 6755,
    "output_tokens": 1700,
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
    "reasoning_output_tokens": 1238,
    "output_tokens_observed": 1700,
    "non_reasoning_output_tokens": 462,
    "visible_output_characters": 1652,
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
    "source": "output[3]",
    "role": "assistant",
    "status": "completed",
    "content": [
      {
        "type": "output_text",
        "annotations": [],
        "logprobs": [],
        "text": "{\"judgments\":[{\"turn_id\":\"1\",\"key\":\"contribution_clarity\",\"level\":4},{\"turn_id\":\"1\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"project_understanding\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"2\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"2\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"3\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"3\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"3\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"3\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"4\",\"key\":\"technical_reasoning\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"problem_solving\",\"level\":3},{\"turn_id\":\"4\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"company_job_fit\",\"level\":3},{\"turn_id\":\"5\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"6\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"6\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"6\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"7\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"7\",\"key\":\"technical_reasoning\",\"level\":4},{\"turn_id\":\"7\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"7\",\"key\":\"communication\",\"level\":3},{\"turn_id\":\"8\",\"key\":\"company_job_fit\",\"level\":\"not_applicable\"},{\"turn_id\":\"8\",\"key\":\"communication\",\"level\":4},{\"turn_id\":\"9\",\"key\":\"project_understanding\",\"level\":2},{\"turn_id\":\"9\",\"key\":\"technical_reasoning\",\"level\":2},{\"turn_id\":\"9\",\"key\":\"problem_solving\",\"level\":\"not_applicable\"},{\"turn_id\":\"9\",\"key\":\"communication\",\"level\":3}]}"
      }
    ]
  }
]
```

</details>

<details>
<summary>생성 텍스트 읽기용 보기 1 — 문자열 해석만 적용</summary>

```text
{"judgments":[{"turn_id":"1","key":"contribution_clarity","level":4},{"turn_id":"1","key":"communication","level":4},{"turn_id":"2","key":"project_understanding","level":4},{"turn_id":"2","key":"technical_reasoning","level":4},{"turn_id":"2","key":"problem_solving","level":"not_applicable"},{"turn_id":"2","key":"communication","level":3},{"turn_id":"3","key":"project_understanding","level":2},{"turn_id":"3","key":"technical_reasoning","level":2},{"turn_id":"3","key":"problem_solving","level":"not_applicable"},{"turn_id":"3","key":"communication","level":3},{"turn_id":"4","key":"project_understanding","level":2},{"turn_id":"4","key":"technical_reasoning","level":3},{"turn_id":"4","key":"problem_solving","level":3},{"turn_id":"4","key":"communication","level":3},{"turn_id":"5","key":"company_job_fit","level":3},{"turn_id":"5","key":"communication","level":4},{"turn_id":"6","key":"project_understanding","level":2},{"turn_id":"6","key":"technical_reasoning","level":4},{"turn_id":"6","key":"problem_solving","level":"not_applicable"},{"turn_id":"6","key":"communication","level":3},{"turn_id":"7","key":"project_understanding","level":2},{"turn_id":"7","key":"technical_reasoning","level":4},{"turn_id":"7","key":"problem_solving","level":"not_applicable"},{"turn_id":"7","key":"communication","level":3},{"turn_id":"8","key":"company_job_fit","level":"not_applicable"},{"turn_id":"8","key":"communication","level":4},{"turn_id":"9","key":"project_understanding","level":2},{"turn_id":"9","key":"technical_reasoning","level":2},{"turn_id":"9","key":"problem_solving","level":"not_applicable"},{"turn_id":"9","key":"communication","level":3}]}
```

</details>

[이 요청이 발생한 원래 SDK 결과 파일](../../../artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/results/gpt-6-luna-3.json)

<details>
<summary>이 슬롯의 최종 사례 회계·기술 관찰</summary>

```json
{
  "model_case_key": "gpt-6-luna::cases/answer/legacy-na-v1::b-legacy-na-01",
  "model_id": "gpt-6-luna",
  "case_id": "b-legacy-na-01",
  "experiment": "B",
  "corpus": "cases/answer/legacy-na-v1",
  "fresh_job_id": "gpt-6-luna-3",
  "status": "succeeded",
  "fresh_result_present": true,
  "display_result_present": true,
  "result_reused": false,
  "result_origin": "C:\\Users\\dreac\\Desktop\\kdt\\model-lab\\runs\\elice-dev30-10usd-20261111-recovery-4",
  "reused_output_sha256": null,
  "identity_inferred": false,
  "identity_inference": null,
  "latency_ms": 38667.0,
  "latency_source": "recorded_sdk_attempt_latency_sum",
  "service_latency_ms_original": null,
  "sdk_latency_missing_attempts": 0,
  "review_status": "unreviewed",
  "quality_denominator": 0,
  "prior_attempt_ids": [],
  "fresh_attempt_ids": [
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-53",
    "C:/Users/dreac/Desktop/kdt/model-lab/runs/elice-dev30-10usd-20261111-recovery-4::attempt-54"
  ],
  "automatic_checks": null,
  "prior_orphan_attempt_present": false,
  "lifetime_attempted": true,
  "fresh_attempted": true,
  "cost": {
    "status": "bounded",
    "cost_usd": null,
    "cost_lower_usd": "0.00258235",
    "cost_upper_usd": "0.00344495",
    "known_confirmed_subtotal_usd": "0",
    "known_tariff_lower_subtotal_usd": "0.00258235",
    "known_tariff_upper_subtotal_usd": "0.00344495",
    "unknown_attempts": 0,
    "bounded_attempts": 2,
    "attempts": 2
  },
  "tokens": {
    "input_known_subtotal": 14730,
    "output_known_subtotal": 3700,
    "input_total": 14730,
    "output_total": 3700,
    "missing_input_attempts": 0,
    "missing_output_attempts": 0,
    "result_sdk_usage_missing_attempts": 0,
    "known_subtotal_includes_identified_transport_orphans": false,
    "unmatched_sdk_attempts": 0,
    "ambiguous_orphan_observations_excluded_from_subtotal": 0,
    "known_subtotal_reconciliation_complete": true
  },
  "B_draft_diagnostic": {
    "expected_pairs": 30,
    "strict_matches": 15,
    "acceptable_matches": 15,
    "na_mismatches": 7,
    "numeric_pairs_compared": 17,
    "numeric_absolute_error_sum": 8,
    "case_id": "b-legacy-na-01",
    "corpus": "cases/answer/legacy-na-v1",
    "predicted": {
      "keys": {
        "project_understanding": 53,
        "technical_reasoning": 72,
        "problem_solving": 70,
        "communication": 77,
        "contribution_clarity": 90,
        "company_job_fit": 70
      },
      "total": 72
    },
    "draft_reference": {
      "keys": {
        "project_understanding": 90,
        "technical_reasoning": 63,
        "problem_solving": 70,
        "communication": 90,
        "contribution_clarity": 90,
        "company_job_fit": 90
      },
      "total": 82
    },
    "absolute_total_deviation": 10,
    "key_absolute_deviations": [
      37,
      9,
      0,
      13,
      0,
      20
    ],
    "approved_correctness": false
  },
  "quality_evaluation_status": "unreviewed_draft_diagnostic_only"
}
```

</details>
