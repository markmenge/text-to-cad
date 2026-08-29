# Suggested filename: run_benchmarks.py

import argparse
import json
from pathlib import Path

from pipeline import run_one

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional OpenAI mode: py -m pip install openai


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--openai",action="store_true")
    args=ap.parse_args()
    root=Path(__file__).resolve().parent
    items=json.loads((root/"benchmarks"/"prompts.json").read_text(encoding="ascii"))
    summary=[]
    for item in items:
        report=run_one(item["prompt"],root/"outputs"/item["id"],args.openai)
        row={"id":item["id"],"difficulty":item["difficulty"],"passed":report["passed"],"strategies":report["brief"]["strategies"],**report["metrics"]}
        summary.append(row)
        print(item["id"],"PASS" if report["passed"] else "FAIL",report["metrics"].get("bbox_mm"),report["reasons"])
    (root/"outputs"/"benchmark_summary.json").write_text(json.dumps(summary,indent=2),encoding="ascii")
    print(f"RESULT {sum(x['passed'] for x in summary)}/{len(summary)}")
    return 0 if all(x["passed"] for x in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
