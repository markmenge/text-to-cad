# Suggested filename: test_v4_mechanical.py

import json
import tempfile
import unittest
from pathlib import Path

from assembly_validator import AssemblyValidator
from mechanical_ir import JointIR, MechanicalSystemIR, PartIR, derive_mechanical_ir
from pipeline_v2 import OpenSCADCompiler
from pipeline_v4 import run_one_v4

# pip install instructions:
# py -m pip install trimesh pillow numpy

ROOT = Path(__file__).resolve().parents[1]
HINGE = "Generate a two-part hinged mechanism demonstrator with one revolute joint from 0 to 110 degrees."
SLIDER = "Generate a two-part slider mechanism demonstrator with one prismatic joint and 30 mm total travel."
CUBE = "Generate a 2 cm by 2 cm by 2 cm cube."


class V4MechanicalTests(unittest.TestCase):
    def test_mechanical_ir_parses_parts_and_joint(self):
        data = {"mechanical_system": {"parts":[
            {"id":"base","role":"base","grounded":True},
            {"id":"arm","role":"arm","origin_mm":[0,0,10]}],
            "joints":[{"id":"J1","type":"revolute","parent":"base","child":"arm","axis":[1,0,0],"origin_mm":[0,0,0],"limits":[0,90],"clearance_mm":0.4}],
            "expected_dof":1}}
        ir = derive_mechanical_ir(data)
        self.assertTrue(ir.is_assembly)
        self.assertEqual(len(ir.parts), 2)
        self.assertEqual(ir.joints[0].type, "revolute")

    def test_explicit_export_contract_writes_named_parts_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            compiler = OpenSCADCompiler()
            build = compiler.build(
                "module base(){cube([10,10,2]);}\n"
                "module arm(){translate([2,2,2]) cube([6,6,2]);}\n"
                "base(); arm();\n",
                out,
            )
            ir = MechanicalSystemIR(
                parts=[
                    PartIR("base", "base", grounded=True, export_name="base.stl", export_module="base"),
                    PartIR("arm", "arm", export_name="arm.stl", export_module="arm"),
                ],
                joints=[],
            )
            result = AssemblyValidator(openscad=compiler.exe).validate_mesh(build.stl_path, ir, out / "parts")
            self.assertTrue(result["pass"])
            self.assertEqual({Path(path).name for path in result["exports"]}, {"base.stl", "arm.stl"})
            self.assertTrue((out / "parts" / "parts_manifest.json").exists())

    def test_clearance_and_dof_are_deterministically_validated(self):
        ir = MechanicalSystemIR(
            parts=[PartIR("base","base",grounded=True), PartIR("arm","arm")],
            joints=[JointIR("J1","revolute","base","arm",[1,0,0],[0,0,0],[0,90],0.1)],
            expected_dof=2,
        )
        result = AssemblyValidator(0.25).validate_ir(ir)
        self.assertFalse(result["pass"])
        self.assertIn("CLEARANCE_FAILURE", result["failure_codes"])
        self.assertIn("JOINT_CONSTRAINT_FAILURE", result["failure_codes"])

    def test_v4_cube_preserves_single_part_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v4(CUBE, Path(td), "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(report["pipeline_version"], "4.1.0-dev2")
            mech = json.loads((Path(td)/"mechanical_ir.json").read_text())
            self.assertEqual(mech, {})

    def test_hinge_repairs_merged_parts_and_exports_named_stls(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            report = run_one_v4(HINGE, out, "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            self.assertIn("PART_COUNT_FAILURE", report["iterations"][0]["failure_codes"])
            self.assertEqual(report["mechanical_summary"]["parts"], 2)
            self.assertEqual(report["mechanical_summary"]["joints"], 1)
            self.assertEqual(set(report["mechanical_summary"]["part_exports"]), {"base.stl","lid.stl"})
            motion=json.loads((out/"motion_samples.json").read_text())
            self.assertEqual(len(motion),3)
            self.assertEqual(motion[0]["joint_type"],"revolute")

    def test_slider_repairs_interference_and_exports_named_stls(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            report = run_one_v4(SLIDER, out, "mock")
            self.assertTrue(report["passed"])
            self.assertEqual(len(report["iterations"]), 2)
            self.assertIn("PART_COUNT_FAILURE", report["iterations"][0]["failure_codes"])
            self.assertEqual(set(report["mechanical_summary"]["part_exports"]), {"guide.stl","slider.stl"})
            motion=json.loads((out/"motion_samples.json").read_text())
            self.assertEqual(motion[-1]["value"],15.0)


if __name__ == "__main__":
    unittest.main()
