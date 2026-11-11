# DEVON model-lab

DEVON 면접 서비스의 **A: 질문 생성(Director)**, **B: 답변 평가(report_score)** 모델을 비교한 독립 실험실입니다. 2026-11-11 Elice에서 실행한 동일한 **16개 dev 입력 × 6개 모델**의 코드, 합성 사례, 예상 판단 기준, 실제 응답, 채점 및 실패 기록을 보존합니다. DEVON 원본은 읽기 전용 외부 의존성으로 유지했습니다.

## 결과부터 보기

- [상세 결과·모델 후보](docs/experiment/RESULTS.md)
- [실험 과정·조건·실패 및 복구 이력](docs/experiment/METHODS.md)
- [16개 사례집: 질문·예상 답변·모델별 실제 출력·채점](docs/experiment/CASEBOOK.md)
- [질문과 예상 답변만 먼저 보기](docs/experiment/QUESTIONS_AND_EXPECTATIONS.md)
- [원본 최종 분석 JSON](artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/analysis.json), [사례·시도별 회계](artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/final-analysis/case-accounting.json)

**잠정 후보는 A에 `gpt-6.1-sol`, B에 정확도 우선 `gpt-6.1-sol` / 비용 우선 `gpt-6-luna`입니다.** A의 선택은 기술적 완료율 11/11에 근거합니다. 질문 내용 품질의 우승을 입증하지는 않았습니다. B의 본 실험 4면접에서 초안 정답과 일치한 판단은 Sol 60/68, Luna 55/68이며 서비스 총점 평균 절대편차는 0.75점, 2점입니다. 합격 임계값은 만들지 않았습니다.

모든 사례와 정답은 **`unreviewed` 합성 초안**입니다. A 의미 평가 Judge 호출은 0회이고 승인된 정답 정확도 분모는 0입니다. B의 legacy NA 면접 1개는 본 실험과 분리했습니다. 모델의 일반적인 성능 순위나 운영 전환 확정으로 해석하면 안 됩니다.

| 보존된 전체 실험 | 값 |
|---|---:|
| 계획된 모델·사례 슬롯 | 96 = A 11 + B 5, 각 6모델 |
| 기술적 상태 | 성공 56 / 실패 23 / 중단 2 / 미실행 15 |
| 실제 HTTP 시도 | 125 (실패·재시도 포함) |
| 보존된 HTTP 응답 원문 | 123 (첫 404·취소 요청 2건의 원문 없음) |
| 사용량 확인 시도의 단가 기준 소계 | $1.209497700–$1.267645900 |
| 사용량 미확인 | 5시도, 4사례; 실제 전체 비용 미확인 |
| 미확인 예약액까지 더한 보수적 노출액 | $1.674892650 / 승인 상한 $10 |

위 금액은 사용자 제공 가격표와 토큰 기록에 따른 계산입니다. 실제 청구액을 확인하지 않았으며 미확인 5시도를 0달러로 처리하지 않았습니다. 업로드를 위해 추가 모델 호출을 하지 않았습니다.

## 파일 구성

| 경로 | 내용 |
|---|---|
| `cases/` | 전체 합성 사례 A 35건, B 17면접의 입력·초안 정답·검수 상태·재질문 연결 |
| `selections/`, `experiments/` | 동결한 동일 dev 16개 선택과 모델 조건 |
| `adapters/`, `run_lab.py`, `run_campaign.py` | 실제 호출 경로와 공통 금액 예산·시도 수 보호 |
| `pricing.yaml`, `cost_*.py`, `elice_billing.py` | 단가·예상/실제 사용량·캐시 비용 범위와 미확인 처리 |
| `schemas/`, `tests/` | 출력 계약과 오프라인 보호 로직 검증 |
| `docs/experiment/` | GitHub에서 읽을 수 있는 상세 보고서·전체 사례집 |
| `artifacts/experiments/elice-dev30-20261111/` | 5개 실행 원본, 원문 출력, 승인·회계·해시, 실행 당시 소스 이력 |
| `FILE_MANIFEST.json` | 게시 파일별 SHA-256과 바이트 수 |

루트 `pricing.yaml`은 초기 미설정 템플릿입니다. 이번 비용에 쓴 여섯 모델의 실제 제공 단가·출처·가격표 버전은 [최종 실행 가격 사본](artifacts/experiments/elice-dev30-20261111/runs/elice-dev30-10usd-20261111-recovery-4/pricing.yaml)에 있습니다. 기존 `manifests/elice-30pct` 역시 초기 4,096토큰 설정이며, 최종 2,000토큰 조건은 아카이브의 manifests와 아래 이식 도구를 기준으로 합니다.

`.env`, 실제 키, 가상환경, 로컬 작업 일지, 관련 없는 실행은 제외했습니다. `artifacts/.../claims`와 `approvals`는 당시 실행의 감사 증거입니다. 현재 실행에서 사용할 승인으로 재사용하지 않습니다. 현재 코드는 실험 종료 후 캐시 쓰기 토큰 별칭 수정이 반영된 버전이며, [당시 소스 이력](artifacts/experiments/elice-dev30-20261111/source-history/README.md)으로 구분합니다.

## API 없이 아카이브 검증

Python 3.12 이상과 표준 라이브러리만 필요합니다. DEVON이나 API 키 없이 파일 해시, 96슬롯, 125시도, 123응답, 미확인 사용량과 비용 노출액을 재검산합니다.

```powershell
python -B tools/verify_published_archive.py
```

`FILE_MANIFEST.json`은 자기 자신을 제외한 게시 파일을 검증합니다. `.git` 및 이력 외 로컬 파일은 대상이 아닙니다.

## DEVON 의존성과 로컬 dry-run

실제 서비스의 프롬프트·Pydantic 계약·점수 산식을 재사용하므로 lab 전체 실행에는 DEVON 별도 체크아웃이 필요합니다. 참고 커밋은 `1bb0e33f30c95d578174208c3ee76192a4016b70`이며 **정확한 기준은 보존된 파일별 해시**입니다. 실행 당시 외부 작업 트리에 기존 변경이 있었으므로 커밋만으로 동일성을 보장하지 않습니다. DEVON 코드를 이 저장소에 복제하지 않았습니다.

원본 manifests와 원본 결과 JSON에는 실행 당시 Windows 절대 경로가 남아 있습니다. 원본 바이트는 그대로 보존했습니다. 다른 PC에서는 다음 도구로 **새 폴더에 경로만 바꾼 최종 2,000 출력 토큰 manifests**를 만듭니다. 도구는 프롬프트 해시를 확인하며 DEVON을 수정하지 않습니다.

```powershell
python -B tools/prepare_portable_manifests.py --devon-root ../devon --output-dir manifests/local-published
```

예를 들어 Sol의 선택된 A 입력으로 호출 없는 계획과 예상 범위를 만들려면 다음과 같이 실행합니다. 단가 또는 예산이 빠진 경우 `blocked_reasons`를 남기며 실행 승인은 만들지 않습니다. 예시 도메인으로 네트워크 요청을 보내지 않습니다.

```powershell
python -B run_lab.py --prepare --experiment A --devon-root ../devon --cases cases/question/benchmark-v1 --manifest manifests/local-published/gpt-6.1-sol.json --selection selections/dev-30pct-v1.json --base-url https://offline-preparation.invalid/v1 --max-http-attempts 22 --output runs/local-a-prepare.json
```

전체 lab을 실행할 때는 `pyproject.toml` 의존성을 설치하고 `DEVON_ROOT` 또는 각 명령의 `--devon-root`로 외부 체크아웃을 지정합니다. 설치 환경은 Python 3.13.7이었으며 `requirements-offline.txt`는 당시 패키지 버전 목록입니다. 완전한 resolver lockfile은 아닙니다. dry-run 인자는 `python -B run_lab.py --help`에서 확인하고 `--manifest manifests/local-published/<model>.json`을 명시합니다. 호출 명령과 별도로 쓰이는 `--execute`는 데이터 검증에 필요하지 않습니다.

**새 실제 실행은 단가·금액 예산·새 실행 계획에 묶인 명시적 승인 없이는 차단됩니다.** 토큰 미확인 시 계속 호출하지 않도록 보호합니다. 당시 $10 승인은 이 아카이브를 읽는 사람의 새로운 실행 승인이 아닙니다.

## 원본 경로·재현 범위

원본의 `.../model-lab/runs/<run>/...` 경로는 이 저장소의 `artifacts/experiments/elice-dev30-20261111/runs/<run>/...`에 대응합니다. [원본 복사 출처·해시](artifacts/experiments/elice-dev30-20261111/publication-provenance.json)를 제공합니다. 원본 분석 스크립트는 `analysis-source/`에 당시 경로 설정을 포함해 보존했으며 이식 가능한 CLI라고 주장하지 않습니다. 오프라인 게시 검증은 위 `verify_published_archive.py`를 사용합니다.

`docs/history/` 및 기존 단계 보고서는 당시 상태를 기록한 참고 자료입니다. 현재 결론과 비용은 `docs/experiment/RESULTS.md`와 원본 `final-analysis/`를 기준으로 읽어 주세요.
