# Suggested filename: test_v4_motion.py

import json
import tempfile
import unittest
from pathlib import Path

from kinematics import part_transforms
from mechanical_ir import JointIR, MechanicalSystemIR, PartIR
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

    def test_four_bar_closure_has_one_driver_and_one_effective_dof(self):
        parts = [
            PartIR("ground", "ground", grounded=True),
            PartIR("crank", "crank"),
            PartIR("coupler", "coupler"),
            PartIR("rocker", "rocker"),
        ]
        joints = [
            JointIR("j1", "revolute", "ground", "crank", [0, 0, 1], [0, 0, 0], [10, 100], 0.5),
            JointIR("j2", "revolute", "crank", "coupler", [0, 0, 1], [30, 0, 0], [0, 180], 0.5),
            JointIR("j3", "revolute", "coupler", "rocker", [0, 0, 1], [0, 0, 0], [0, 180], 0.5),
            JointIR("j4", "revolute", "rocker", "ground", [0, 0, 1], [80, 0, 0], [0, 180], 0.5),
        ]
        ir = MechanicalSystemIR(
            parts, joints, expected_dof=1,
            closed_loops=[{
                "type": "four_bar", "parts": {"crank": "crank", "coupler": "coupler", "rocker": "rocker"},
                "link_lengths_mm": {"crank": 30, "coupler": 55, "rocker": 55},
                "ground_pivots_mm": [[0, 0], [80, 0]], "input_joint": "j1",
                "nominal_input_deg": 45, "branch": 1,
            }],
        )
        self.assertEqual(len(__import__("kinematics").motion_configurations(ir)), 3)
        transforms = part_transforms(ir, {"j1": 10})
        self.assertEqual(set(transforms), {"ground", "crank", "coupler", "rocker"})

    def test_four_bar_runs_through_explicit_exports_and_motion_validation(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v4("Generate a four-bar linkage demonstrator with one driven crank.", Path(td), "mock", max_iterations=3)
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            self.assertIn("EXPORT_CONTRACT_FAILURE", report["iterations"][0]["failure_codes"])
            self.assertEqual(report["mechanical_summary"]["parts"], 4)
            self.assertEqual(set(report["mechanical_summary"]["part_exports"]), {"ground.stl", "crank.stl", "coupler.stl", "rocker.stl"})
            motion = report["iterations"][-1]["metrics"]["motion_validation"]
            self.assertTrue(motion["pass"])
            self.assertEqual(motion["sample_count"], 3)
            self.assertEqual(motion["collision_count"], 0)


if __name__ == "__main__":
    unittest.main()
