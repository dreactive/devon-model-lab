"""Calculate offline costs from saved attempts; never execute a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from cost_accounting import load_pricing, summarize_results

LAB_ROOT = Path(__file__).resolve().parent


def display(value: object) -> str:
    return "미수집/미확인" if value is None else str(value)


def markdown(report: dict) -> str:
    lines = [
        "# 비용·품질 병렬 보고", "",
        "저장된 시도 기록의 사후 계산이다. 예상 비용이나 모델 실행 결과를 새로 만들지 않는다.",
        "미검수 품질은 집계하지 않으며 누락 단가·사용량은 0으로 채우지 않는다.", "",
        "| 모델 | 총 비용 USD | 알려진 부분합 USD | 사례당 USD | 인터뷰당 USD | 정답 일치당 USD | 실패율 | 재시도·실패 비용 비율 | 지연 p50/p95 ms | 서비스 점수 편차 | 입력/출력 토큰 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for model, row in report.get("models", {}).items():
        averages = row.get("averages", {})
        efficiency = row.get("efficiency", {})
        latency = row.get("latency_ms", {})
        counts = row.get("counts", {})
        executed = counts.get("executed_cases", 0)
        failures = counts.get("service_failures", 0)
        failure_rate = f"{failures}/{executed}" if executed else "미수집"
        tokens = row.get("tokens", {})
        input_total = tokens.get("input_tokens", {}).get("total")
        output_total = tokens.get("output_tokens", {}).get("total")
        lines.append(
            f"| {model.replace('|', '/')} | {display(row.get('total_usd'))} | "
            f"{display(row.get('known_subtotal_usd'))} | "
            f"{display(averages.get('service_per_case_usd'))} | "
            f"{display(averages.get('service_per_interview_usd'))} | "
            f"{display(efficiency.get('cost_per_confirmed_correct_usd'))} | {failure_rate} | "
            f"{display(row.get('waste', {}).get('retry_or_failure_share'))} | "
            f"{display(latency.get('p50'))}/{display(latency.get('p95'))} | "
            f"{display(row.get('quality', {}).get('service_score_deviation'))} | "
            f"{display(input_total)}/{display(output_total)} |"
        )
    if not report.get("models"):
        lines.append("| 모델 미실행 | 미수집 | 해당 없음 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 |")
    counts = report.get("counts", {})
    lines.extend([
        "", f"전체 비용 상태: {report.get('status_ko', report.get('status'))}",
        f"전체 총 비용 USD: {display(report.get('total_usd'))}",
        f"알려진 부분합 USD: {display(report.get('known_subtotal_usd'))}",
        f"미확인 사례 수: {counts.get('unknown_cases', 0)} / 사용량 누락 사례 수: {counts.get('missing_token_cases', 0)} / 단가 미수집 사례 수: {counts.get('missing_price_cases', 0)}",
        f"모델 미실행 사례 수: {counts.get('not_executed_cases', 0)}",
        "", "누락·실패·재시도와 Judge 비용의 상세 분모는 함께 저장한 JSON을 참조한다.",
        "숫자로 수집하지 않은 품질·점수 편차·지연은 미수집으로 남긴다. 합격 임계값은 정하지 않는다.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    parser.add_argument("--pricing", type=Path, default=LAB_ROOT / "pricing.yaml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        devon = Path(os.environ.get("DEVON_ROOT", LAB_ROOT.parent / "devon")).resolve()
        outputs = [args.output] + ([args.markdown] if args.markdown else [])
        inputs = {path.resolve() for path in [*args.results, args.pricing]}
        if len({path.resolve() for path in outputs}) != len(outputs):
            raise ValueError("duplicate_output")
        for path in outputs:
            if path.resolve().is_relative_to(devon) or path.resolve() in inputs or path.exists():
                raise ValueError("output_rejected")
        sources, results = [], []
        for path in args.results:
            raw = path.read_bytes()
            results.append(json.loads(raw.decode("utf-8-sig")))
            sources.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
        report = summarize_results(results, load_pricing(args.pricing))
        report["result_sources"] = sources
        report["pricing_sha256"] = hashlib.sha256(args.pricing.read_bytes()).hexdigest()
        report["model_calls"] = 0
        for path in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        if args.markdown:
            with args.markdown.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(markdown(report))
    except Exception:
        print(json.dumps({"status": "failed", "error": "cost_report_rejected", "model_calls": 0}))
        return 1
    print(json.dumps({"status": report["status"], "total_usd": report["total_usd"],
                      "known_subtotal_usd": report["known_subtotal_usd"],
                      "counts": report["counts"], "model_calls": 0}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
