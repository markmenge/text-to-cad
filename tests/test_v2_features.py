# Suggested filename: test_v2_features.py

import json
import tempfile
import unittest
from pathlib import Path

from llm_client import LLMRequest, MockOpenAIClient, ReplayClient, _request_key
from pipeline_v2 import create_llm, run_one

# pip install instructions:
# py -m pip install trimesh pillow numpy

ROOT = Path(__file__).resolve().parents[1]
CUBE = "Generate a 2 cm by 2 cm by 2 cm cube."


class V2FeatureTests(unittest.TestCase):
    def test_live_mode_alias_uses_openai_client(self):
        client = create_llm("live", ROOT)
        self.assertEqual(type(client).__name__, "OpenAIClient")

    def test_run_bundle_contains_observability_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            report = run_one(CUBE, out, "mock")
            self.assertTrue(report["passed"])
            for name in ("run.json", "prompt.txt", "planner_brief.json", "planner_call.json", "report.json", "postmortem.md"):
                self.assertTrue((out / name).exists(), name)
            idir = out / "iteration_01"
            for name in ("generator_call.json", "critic_call.json", "validator.json", "iteration_summary.json", "openscad_stl_stdout.txt", "openscad_stl_stderr.txt"):
                self.assertTrue((idir / name).exists(), name)
            self.assertEqual(len(list(idir.glob("view_*.png"))), 4)
            self.assertTrue((out / "final" / "model.stl").exists())

    def test_requirement_ledger_and_prompt_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one(CUBE, Path(td), "mock")
            self.assertTrue(report["prompt_hashes"])
            reqs = report["iterations"][0]["requirement_results"]
            self.assertTrue(all(r["id"].startswith("R") for r in reqs))
            connected = [r for r in reqs if "connected" in r["text"].lower()]
            self.assertTrue(connected)
            self.assertEqual(connected[0]["status"], "PASS")

    def test_replay_client_replays_recorded_requests(self):
        mock = MockOpenAIClient(ROOT / "mocks" / "mock_openai.json", ROOT / "prompts")
        req = LLMRequest("planner", CUBE, {})
        response = mock.generate(req)
        cassette = {
            "calls": [{
                "request_key": _request_key(req),
                "role": req.role,
                "request": {"role": req.role, "prompt": req.prompt, "context": req.context},
                "response_text": response.text,
                "metadata": {"source": "unit_test"},
            }]
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cassette.json"
            path.write_text(json.dumps(cassette), encoding="utf-8")
            replay = ReplayClient(path, ROOT / "prompts")
            got = replay.generate(req)
            self.assertEqual(got.text, response.text)
            self.assertEqual(got.metadata["mode"], "replay")


if __name__ == "__main__":
    unittest.main()
