# Suggested filename: test_pipeline_offline.py

import tempfile
import unittest
from pathlib import Path

from pipeline_v2 import run_one

# pip install instructions:
# py -m pip install trimesh pillow numpy


class OfflinePipelineTests(unittest.TestCase):
    def test_cube_one_iteration(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one("Generate a 2 cm by 2 cm by 2 cm cube.", Path(td), "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 1)
            self.assertEqual(report["iterations"][0]["generator_fixture"], "gen_cube")

    def test_f16_repairs_from_validator_feedback(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one("Generate a F-16 model.", Path(td), "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            first, second = report["iterations"]
            self.assertFalse(first["deterministic_pass"])
            self.assertIn("connected components=", " ".join(first["feedback"]))
            self.assertEqual(second["generator_fixture"], "gen_f16_repair")

    def test_frog_repairs_from_critic_feedback(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one("Generate a tea cup with a frog in it.", Path(td), "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            first, second = report["iterations"]
            self.assertTrue(first["deterministic_pass"])
            self.assertFalse(first["semantic_pass"])
            self.assertEqual(first["critic_fixture"], "critic_frog_first")
            self.assertEqual(second["generator_fixture"], "gen_frog_teacup_repair")


if __name__ == "__main__":
    unittest.main()

class OfflineFaultInjectionTests(unittest.TestCase):
    def test_compile_error_is_repaired_from_feedback(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one("offline compile repair test", Path(td), "mock", max_iterations=3)
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            first, second = report["iterations"]
            self.assertFalse(first["deterministic_pass"])
            self.assertIn("OpenSCAD STL compile failed", first["feedback"])
            self.assertEqual(second["generator_fixture"], "gen_compile_error_repair")

    def test_retry_limit_stops_permanent_failure(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one("always fail cad", Path(td), "mock", max_iterations=2)
            self.assertFalse(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            self.assertTrue(all(not x["deterministic_pass"] for x in report["iterations"]))
