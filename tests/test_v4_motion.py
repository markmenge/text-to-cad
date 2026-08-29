# Suggested filename: test_v4_motion.py

import json
import tempfile
import unittest
from pathlib import Path

from pipeline_v4 import run_one_v4

# pip install instructions:
# py -m pip install trimesh pillow numpy

MOTION_COLLISION = "Generate a two-part motion-collision revolute demonstrator with 0 to 90 degree travel."
TWO_JOINT = "Generate a three-part two-joint serial revolute arm demonstrator with two independent revolute joints."
HINGE = "Generate a two-part hinged mechanism demonstrator with one revolute joint from 0 to 110 degrees."


class V4MotionTests(unittest.TestCase):
    def test_motion_collision_enters_repair_loop(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v4(MOTION_COLLISION, Path(td), "mock", max_iterations=3)
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            first = report["iterations"][0]
            self.assertIn("MOTION_COLLISION_FAILURE", first["failure_codes"])
            self.assertEqual(report["iterations"][1]["repair_route"], "kinematic_interference_repair")
            self.assertGreater(first["metrics"]["motion_validation"]["collision_count"], 0)
            final_motion = json.loads((Path(td) / "motion_validation.json").read_text())
            self.assertTrue(final_motion["pass"])
            self.assertEqual(final_motion["collision_count"], 0)

    def test_two_joint_chain_samples_cartesian_motion(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            report = run_one_v4(TWO_JOINT, out, "mock", max_iterations=3)
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            self.assertEqual(report["mechanical_summary"]["parts"], 3)
            self.assertEqual(report["mechanical_summary"]["joints"], 2)
            self.assertEqual(set(report["mechanical_summary"]["part_exports"]), {"base.stl", "arm1.stl", "arm2.stl"})
            motion = report["iterations"][-1]["metrics"]["motion_validation"]
            self.assertTrue(motion["pass"])
            self.assertEqual(motion["sample_count"], 9)
            self.assertEqual(motion["collision_count"], 0)
            configs = json.loads((out / "motion_configurations.json").read_text())
            self.assertEqual(len(configs), 9)
            self.assertTrue(all(len(c["joint_values"]) == 2 for c in configs))

    def test_hinge_motion_validates_true_axis_clearance(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v4(HINGE, Path(td), "mock", max_iterations=3)
            self.assertTrue(report["passed"])
            motion = report["iterations"][-1]["metrics"]["motion_validation"]
            self.assertTrue(motion["pass"])
            self.assertEqual(motion["sample_count"], 3)
            self.assertEqual(motion["collision_count"], 0)
            self.assertGreaterEqual(motion["minimum_pair_clearance_mm"]["base|lid"], 0.4)


if __name__ == "__main__":
    unittest.main()
