# Suggested filename: knowledge_capture.py

import hashlib
import json
from pathlib import Path

# pip install instructions:
# No third-party packages required.


def capture_success(root: Path, report: dict, engineering_ir: dict, retrieved: list[dict]) -> Path | None:
    if not report.get("passed"):
        return None
    key = hashlib.sha256((report.get("prompt", "") + json.dumps(engineering_ir, sort_keys=True)).encode("utf-8")).hexdigest()[:16]
    out = root / "knowledge" / "successes"
    out.mkdir(parents=True, exist_ok=True)
    final_it = report.get("iterations", [{}])[-1]
    data = {
        "id": key,
        "prompt": report.get("prompt"),
        "object_type": engineering_ir.get("object_type"),
        "primary_strategy": engineering_ir.get("primary_strategy"),
        "secondary_strategies": engineering_ir.get("secondary_strategies", []),
        "subsystems": engineering_ir.get("subsystems", []),
        "final_metrics": final_it.get("metrics", {}),
        "iterations": len(report.get("iterations", [])),
        "retrieved_patterns": [x.get("path") for x in retrieved],
        "pipeline_version": report.get("pipeline_version"),
    }
    json_path = out / f"{key}.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md = [
        f"# Validated CAD Success {key}", "",
        f"Prompt: {data['prompt']}",
        f"Object type: {data['object_type']}",
        f"Primary strategy: {data['primary_strategy']}",
        f"Secondary strategies: {', '.join(data['secondary_strategies']) or 'none'}",
        f"Subsystems: {', '.join(data['subsystems']) or 'body'}",
        f"Validated iterations: {data['iterations']}",
        f"Pipeline version: {data['pipeline_version']}", "",
        "This record comes from a run that passed deterministic geometry validation and semantic critique.",
    ]
    (out / f"{key}.md").write_text("\n".join(md) + "\n", encoding="ascii", errors="replace")
    return json_path
