# Suggested filename: run_benchmarks_v2.py

import argparse
import json
from collections import Counter
from pathlib import Path

from pipeline_v2 import run_one

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional online mode: py -m pip install openai


def main():
    parser = argparse.ArgumentParser(description="Run the Text-to-CAD v2 benchmark suite.")
    parser.add_argument("--llm", choices=["mock", "replay", "openai"], default="mock")
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--cassette", type=Path)
    parser.add_argument("--only", help="Run one benchmark id, e.g. 03_frog_teacup")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    prompts = json.loads((root / "benchmarks" / "prompts.json").read_text(encoding="ascii"))
    if args.only:
        prompts = [p for p in prompts if p["id"] == args.only]
        if not prompts:
            raise SystemExit(f"Unknown benchmark id: {args.only}")

    output_root = root / "runs" / f"benchmark_{args.llm}"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = []

    for item in prompts:
        report = run_one(item["prompt"], output_root / item["id"], args.llm, args.max_iterations, args.cassette)
        last = report["iterations"][-1] if report.get("iterations") else {}
        row = {
            "id": item["id"], "difficulty": item["difficulty"], "passed": report["passed"],
            "iteration_count": len(report.get("iterations", [])),
            "first_pass_success": report.get("metrics_summary", {}).get("first_pass_success", False),
            "repair_count": report.get("metrics_summary", {}).get("repair_count", 0),
            "final_score": report.get("metrics_summary", {}).get("final_score", 0),
            "elapsed_s": report.get("elapsed_s", 0),
            "failure_codes": report.get("final_failure_codes", []),
            "bbox_mm": last.get("metrics", {}).get("bbox_mm"),
            "components": last.get("metrics", {}).get("components"),
            "watertight": last.get("metrics", {}).get("watertight"),
        }
        summary.append(row)
        print(f"{item['id']}: {'PASS' if row['passed'] else 'FAIL'} iterations={row['iteration_count']} score={row['final_score']} elapsed={row['elapsed_s']}s")

    failure_counts = Counter(code for row in summary for code in row["failure_codes"])
    aggregate = {
        "mode": args.llm,
        "total": len(summary),
        "passed": sum(r["passed"] for r in summary),
        "success_rate": round(sum(r["passed"] for r in summary) / len(summary), 4) if summary else 0,
        "first_pass_rate": round(sum(r["first_pass_success"] for r in summary) / len(summary), 4) if summary else 0,
        "average_iterations": round(sum(r["iteration_count"] for r in summary) / len(summary), 3) if summary else 0,
        "average_elapsed_s": round(sum(r["elapsed_s"] for r in summary) / len(summary), 3) if summary else 0,
        "failure_distribution": dict(failure_counts),
        "benchmarks": summary,
    }
    (output_root / "benchmark_summary.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(f"RESULT {aggregate['passed']}/{aggregate['total']} success={aggregate['success_rate']:.0%}")
    return 0 if aggregate["passed"] == aggregate["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
