# Suggested filename: make_cassette.py

import argparse
import json
from pathlib import Path

from llm_client import LLMRequest, _request_key

# pip install instructions:
# No third-party packages required.


def main():
    parser = argparse.ArgumentParser(description="Convert a completed run's LLM call logs into a replay cassette.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("cassette", type=Path)
    args = parser.parse_args()

    call_files = [args.run_dir / "planner_call.json"]
    for idir in sorted(args.run_dir.glob("iteration_*")):
        call_files.extend([idir / "generator_call.json", idir / "critic_call.json"])

    calls = []
    for path in call_files:
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        req = LLMRequest(record["role"], record["prompt"], record["context"])
        calls.append({
            "request_key": _request_key(req),
            "role": req.role,
            "request": {"role": req.role, "prompt": req.prompt, "context": req.context},
            "response_text": record["response_text"],
            "fixture_id": record.get("fixture_id"),
            "metadata": record.get("metadata", {}),
        })

    args.cassette.parent.mkdir(parents=True, exist_ok=True)
    run_meta = json.loads((args.run_dir / "run.json").read_text(encoding="utf-8")) if (args.run_dir / "run.json").exists() else {}
    args.cassette.write_text(json.dumps({"prompt_hashes": run_meta.get("prompt_hashes", {}), "calls": calls}, indent=2), encoding="utf-8")
    print(f"Wrote {len(calls)} calls to {args.cassette}")


if __name__ == "__main__":
    main()
