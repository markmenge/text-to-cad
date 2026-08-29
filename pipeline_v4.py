# Suggested filename: pipeline_v4.py

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from assembly_validator import AssemblyValidator
from engineering_ir import derive_ir
from kinematics import motion_configurations, sample_motion
from llm_client import LLMRequest
from mechanical_ir import derive_mechanical_ir
from motion_validator import MotionCollisionValidator
from pipeline_v2 import DeterministicValidator, LLMCritic, Requirement, create_llm
from pipeline_v3 import KnowledgeAwarePlanner, V3CADController
from version import PIPELINE_VERSION

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional online mode: py -m pip install openai


class MechanicalAwarePlanner(KnowledgeAwarePlanner):
    def __init__(self, llm, retriever, manufacturing_profile):
        super().__init__(llm, retriever, manufacturing_profile)
        self.last_mechanical_ir = None

    def plan(self, prompt: str):
        brief, fixture = super().plan(prompt)
        self.last_mechanical_ir = derive_mechanical_ir(self.last_raw or {})
        if self.last_mechanical_ir and self.last_mechanical_ir.is_assembly:
            brief.requirements = [
                r for r in brief.requirements
                if not (r.type == "manufacturing" and "one connected printable object" in r.text.lower())
            ]
            if not any("individually printable" in r.text.lower() for r in brief.requirements):
                brief.requirements.append(Requirement(
                    id=f"R{len(brief.requirements)+1}",
                    type="manufacturing",
                    text="Each assembly part is individually printable",
                ))
            if not any("joint" in r.text.lower() for r in brief.requirements):
                brief.requirements.append(Requirement(
                    id=f"R{len(brief.requirements)+1}",
                    type="mechanical",
                    text="Joint graph and degrees of freedom match the requested mechanism",
                ))
        return brief, fixture


class MechanicalAwareGenerator:
    def __init__(self, llm, planner: MechanicalAwarePlanner):
        self.llm = llm
        self.planner = planner

    def generate(self, brief, feedback, failure_codes, repair_route, iteration):
        context = {
            "object_type": brief.object_type,
            "strategies": brief.strategies,
            "dimensions_mm": brief.dimensions_mm,
            "requirements": [asdict(r) for r in brief.requirements],
            "feedback": feedback,
            "failure_codes": failure_codes,
            "repair_route": repair_route,
            "iteration": iteration,
            "engineering_ir": self.planner.last_ir.to_dict() if self.planner.last_ir else {},
            "mechanical_ir": self.planner.last_mechanical_ir.to_dict() if self.planner.last_mechanical_ir else {},
            "retrieved_patterns": self.planner.retriever.serializable(self.planner.last_retrieved),
            "manufacturing_profile": self.planner.manufacturing_profile.to_dict(),
        }
        response = self.llm.generate(LLMRequest(role="generator", prompt=brief.prompt, context=context))
        text = response.text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1])
        return text + "\n", response.fixture_id


class V4Critic(LLMCritic):
    def __init__(self, llm, planner: MechanicalAwarePlanner):
        super().__init__(llm)
        self.planner = planner

    def critique(self, brief, scad, metrics, deterministic_feedback, requirement_results, image_paths, iteration):
        context = {
            "object_type": brief.object_type,
            "strategies": brief.strategies,
            "requirements": [asdict(r) for r in brief.requirements],
            "requirement_results": requirement_results,
            "iteration": iteration,
            "feedback": deterministic_feedback,
            "metrics": metrics,
            "scad_excerpt": scad[:8000],
            "image_paths": image_paths,
            "engineering_ir": self.planner.last_ir.to_dict() if self.planner.last_ir else {},
            "mechanical_ir": self.planner.last_mechanical_ir.to_dict() if self.planner.last_mechanical_ir else {},
        }
        response = self.llm.generate(LLMRequest(role="critic", prompt=brief.prompt, context=context))
        data = json.loads(response.text)
        return bool(data["pass"]), int(data["score"]), list(data.get("feedback", [])), data.get("requirement_results", []), response.fixture_id


class V4Validator(DeterministicValidator):
    def __init__(self, manufacturing, planner: MechanicalAwarePlanner, openscad: str | None = None):
        self.manufacturing = manufacturing
        self.planner = planner
        self.assembly = AssemblyValidator(
            minimum_moving_clearance_mm=manufacturing.profile.xy_clearance_mm,
            openscad=openscad,
        )
        self.last_manufacturing = None
        self.last_assembly = None
        self.motion = MotionCollisionValidator(openscad=openscad, samples_per_joint=3, max_configurations=27)
        self.last_motion = None

    def validate(self, brief, build):
        passed, reasons, codes, metrics, reqs = DeterministicValidator.validate(self, brief, build)
        mech = self.planner.last_mechanical_ir

        if mech and mech.is_assembly and metrics.get("components") == len(mech.parts):
            codes = [c for c in codes if c != "DISCONNECTED_COMPONENTS"]
            reasons = [r for r in reasons if not r.startswith("connected components=")]

        self.last_manufacturing = self.manufacturing.validate_metrics(metrics)
        metrics["manufacturing"] = self.last_manufacturing
        if not self.last_manufacturing["pass"]:
            codes.append("PRINTABILITY_FAILURE")
            reasons.extend(self.last_manufacturing["failures"])

        ir_result = self.assembly.validate_ir(mech)
        mesh_result = {"pass": True, "failures": [], "failure_codes": [], "exports": []}
        if mech and mech.is_assembly and build.stl_rc == 0 and Path(build.stl_path).exists():
            mesh_result = self.assembly.validate_mesh(
                build.stl_path, mech, export_dir=Path(build.stl_path).parent / "parts"
            )
        self.last_assembly = {"ir": ir_result, "mesh": mesh_result}
        metrics["assembly"] = self.last_assembly
        codes.extend(ir_result.get("failure_codes", []))
        codes.extend(mesh_result.get("failure_codes", []))
        reasons.extend(ir_result.get("failures", []))
        reasons.extend(mesh_result.get("failures", []))

        # V4 Milestone 2: validate actual exported meshes through sampled joint travel.
        self.last_motion = {"pass": True, "failure_codes": [], "failures": [], "configurations": [], "collision_count": 0}
        if mech and mech.is_assembly and mesh_result.get("pass") and mesh_result.get("exports"):
            part_dir = Path(build.stl_path).parent / "parts"
            part_paths = {p.id: part_dir / f"{p.id}.stl" for p in mech.parts}
            self.last_motion = self.motion.validate(
                mech, part_paths, evidence_dir=Path(build.stl_path).parent / "motion_evidence"
            )
            codes.extend(self.last_motion.get("failure_codes", []))
            reasons.extend(self.last_motion.get("failures", []))
        metrics["motion_validation"] = self.last_motion
        codes = list(dict.fromkeys(codes))
        reasons = list(dict.fromkeys(reasons))

        if mech and mech.is_assembly:
            reqs.append({
                "id": "M1", "type": "mechanical", "text": "Assembly structure is valid",
                "status": "PASS" if ir_result["pass"] else "FAIL",
                "evidence": f"parts={len(mech.parts)}, joints={len(mech.joints)}, estimated_dof={ir_result.get('estimated_dof')}"
            })
            reqs.append({
                "id": "M2", "type": "mechanical", "text": "Generated mesh contains the expected separately printable parts",
                "status": "PASS" if mesh_result["pass"] else "FAIL",
                "evidence": f"components={mesh_result.get('component_count')}, expected={mesh_result.get('expected_component_count')}"
            })
            reqs.append({
                "id": "M3", "type": "mechanical", "text": "Sampled joint travel is free of mesh interference and respects moving clearance",
                "status": "PASS" if self.last_motion.get("pass") else ("UNKNOWN" if not mesh_result.get("pass") else "FAIL"),
                "evidence": f"samples={self.last_motion.get('sample_count', 0)}, collisions={self.last_motion.get('collision_count', 0)}"
            })
        return not codes, reasons, codes, metrics, reqs


class V4CADController(V3CADController):
    def __init__(self, llm, root: Path, max_iterations: int = 3, profile=None):
        super().__init__(llm, root=root, max_iterations=max_iterations, profile=profile)
        planner = MechanicalAwarePlanner(llm, self.retriever, self.manufacturing_profile)
        self.planner = planner
        self.generator = MechanicalAwareGenerator(llm, planner)
        self.validator = V4Validator(self.manufacturing, planner, openscad=self.compiler.exe)
        self.critic = V4Critic(llm, planner)

    def _run_metadata(self, prompt: str, mode: str, run_id: str):
        data = super()._run_metadata(prompt, mode, run_id)
        data["pipeline_version"] = PIPELINE_VERSION
        data["v4_features"] = [
            "multi_body_mechanical_ir", "joint_graph_validation", "dof_validation",
            "moving_joint_clearance_validation", "per_part_stl_export", "kinematic_motion_sampling",
            "mesh_motion_collision_validation", "serial_joint_transform_propagation",
        ]
        return data

    def run(self, prompt: str, out: Path, mode: str = "mock"):
        report = super().run(prompt, out, mode=mode)
        mech = self.planner.last_mechanical_ir
        mechanical_dict = mech.to_dict() if mech else {}
        (out / "mechanical_ir.json").write_text(json.dumps(mechanical_dict, indent=2), encoding="utf-8")
        motion = sample_motion(mech, samples_per_joint=3)
        (out / "motion_samples.json").write_text(json.dumps(motion, indent=2), encoding="utf-8")
        motion_configs = motion_configurations(mech, samples_per_joint=3, max_configurations=27)
        (out / "motion_configurations.json").write_text(json.dumps(motion_configs, indent=2), encoding="utf-8")
        if self.validator.last_motion is not None:
            (out / "motion_validation.json").write_text(json.dumps(self.validator.last_motion, indent=2), encoding="utf-8")
        if report.get("passed") and mech and mech.is_assembly:
            last_iter = out / f"iteration_{len(report.get('iterations', [])):02d}" / "parts"
            final_parts = out / "final" / "parts"
            if last_iter.exists():
                if final_parts.exists():
                    shutil.rmtree(final_parts)
                shutil.copytree(last_iter, final_parts)
            report["mechanical_summary"] = {
                "parts": len(mech.parts), "joints": len(mech.joints),
                "motion_samples": len(motion), "part_exports": sorted(p.name for p in final_parts.glob("*.stl")) if final_parts.exists() else [],
            }
            (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report


def run_one_v4(prompt: str, out: Path, mode: str = "mock", max_iterations: int = 3, cassette: Path | None = None):
    root = Path(__file__).resolve().parent
    controller = V4CADController(create_llm(mode, root, cassette), root=root, max_iterations=max_iterations)
    return controller.run(prompt, out, mode=mode)
