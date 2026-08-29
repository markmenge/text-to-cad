# Suggested filename: run_v4_m2_benchmarks.py

import json
import sys
from pathlib import Path

from pipeline_v4 import run_one_v4

# pip install instructions:
# py -m pip install trimesh pillow numpy

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / "benchmarks" / "prompts_v4_m2.json").read_text())
OUT = ROOT / "runs" / "v4_milestone2_benchmark"
OUT.mkdir(parents=True, exist_ok=True)

selected = set(sys.argv[1:])
rows = []
for case in CASES:
    if selected and case["id"] not in selected:
        continue
    report = run_one_v4(case["prompt"], OUT / case["id"], "mock", max_iterations=3)
    final = report.get("iterations", [])[-1] if report.get("iterations") else {}
    motion = final.get("metrics", {}).get("motion_validation", {})
    row = {
        "id": case["id"], "difficulty": case["difficulty"], "passed": bool(report.get("passed")),
        "iterations": len(report.get("iterations", [])), "final_score": final.get("score"),
        "motion_samples": motion.get("sample_count", 0), "motion_collisions": motion.get("collision_count", 0),
        "part_exports": report.get("mechanical_summary", {}).get("part_exports", []),
    }
    rows.append(row)
    print(json.dumps(row))

summary_path = OUT / ("summary_" + ("_".join(sys.argv[1:]) if selected else "all") + ".json")
summary_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(summary_path)
