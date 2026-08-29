# Suggested filename: test_v3_features.py

import json
import tempfile
import unittest
from pathlib import Path

from engineering_ir import derive_ir
from manufacturing import ManufacturingProfile, ManufacturingValidator
from pipeline_v3 import run_one_v3
from retrieval import CorpusRetriever

# pip install instructions:
# py -m pip install trimesh pillow numpy

ROOT = Path(__file__).resolve().parents[1]
CUBE = "Generate a 2 cm by 2 cm by 2 cm cube."
F16 = "Generate a F-16 model."


class V3FeatureTests(unittest.TestCase):
    def test_retriever_prefers_aircraft_pattern_for_f16(self):
        r = CorpusRetriever([ROOT / "corpus" / "patterns", ROOT / "research"])
        results = r.search(F16, limit=3)
        self.assertTrue(results)
        self.assertIn("aircraft", Path(results[0].path).stem.lower())

    def test_engineering_ir_derives_subsystems(self):
        data = {"object_type":"f16", "strategies":["hull_loft","symmetry"], "requirements":["recognizable silhouette"]}
        ir = derive_ir(F16, data, ["aircraft.md"])
        self.assertEqual(ir.primary_strategy, "hull_loft")
        self.assertIn("wings", ir.subsystems)
        self.assertEqual(ir.symmetry, "bilateral")

    def test_manufacturing_profile_rejects_oversize_bbox(self):
        m = ManufacturingValidator(ManufacturingProfile(build_volume_mm=(100, 100, 100)))
        result = m.validate_metrics({"bbox_mm":[120, 20, 20]})
        self.assertFalse(result["pass"])
        self.assertTrue(result["failures"])

    def test_v3_cube_run_writes_new_artifacts_and_captures_knowledge(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v3(CUBE, Path(td), "mock")
            self.assertTrue(report["passed"])
            self.assertTrue((Path(td) / "retrieval_context.json").exists())
            self.assertTrue((Path(td) / "engineering_ir.json").exists())
            self.assertTrue((Path(td) / "manufacturing_profile.json").exists())
            ir = json.loads((Path(td) / "engineering_ir.json").read_text())
            self.assertEqual(ir["object_type"], "cube")
            self.assertEqual(report["pipeline_version"], "4.1.0-dev2")
            self.assertTrue(report.get("knowledge_capture"))

    def test_validated_success_becomes_retrievable_on_next_controller(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_one_v3(CUBE, Path(td), "mock")
            self.assertTrue(report["passed"])
            r = CorpusRetriever([ROOT / "knowledge" / "successes"])
            results = r.search("20 mm cube primitive csg", limit=5)
            self.assertTrue(results)
            self.assertIn("Validated CAD Success", Path(results[0].path).read_text())


if __name__ == "__main__":
    unittest.main()
