# Suggested filename: assembly_validator.py

import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np
import trimesh

from mechanical_ir import MechanicalSystemIR

# pip install instructions:
# py -m pip install trimesh numpy


MOVING_JOINTS = {"revolute", "prismatic"}
ALLOWED_JOINTS = {"fixed", "revolute", "prismatic"}


def _norm(v):
    return math.sqrt(sum(float(x) * float(x) for x in v))


class AssemblyValidator:
    def __init__(self, minimum_moving_clearance_mm: float = 0.25, openscad: str | None = None):
        self.minimum_moving_clearance_mm = float(minimum_moving_clearance_mm)
        self.openscad = openscad

    @staticmethod
    def _has_export_contract(ir: MechanicalSystemIR) -> bool:
        return bool(ir.parts) and all(part.export_name and part.export_module for part in ir.parts)

    def _export_contract_parts(self, scad_path: Path, ir: MechanicalSystemIR, export_dir: Path) -> dict:
        if not self.openscad:
            return {
                "pass": False, "failures": ["Explicit part export contract requires an OpenSCAD executable"],
                "failure_codes": ["EXPORT_CONTRACT_FAILURE"], "exports": [], "manifest": [],
            }
        export_dir.mkdir(parents=True, exist_ok=True)
        exports = []
        manifest = []
        failures = []
        for part in ir.parts:
            target = export_dir / part.export_name
            wrapper = export_dir / f".{part.id}_export.scad"
            wrapper.write_text(
                f'use <{scad_path.resolve().as_posix()}>;\n{part.export_module}();\n',
                encoding="ascii",
            )
            result = subprocess.run(
                [self.openscad, "-o", str(target), str(wrapper)],
                capture_output=True, text=True,
            )
            entry = {
                "part_id": part.id, "export_name": part.export_name,
                "export_module": part.export_module, "path": str(target),
                "returncode": result.returncode,
            }
            manifest.append(entry)
            if result.returncode != 0 or not target.exists() or target.stat().st_size == 0:
                failures.append(f"Explicit export failed for part {part.id}")
            else:
                mesh = trimesh.load_mesh(target, process=True)
                if not mesh.is_watertight or abs(float(mesh.volume)) <= 0:
                    failures.append(f"Explicit export for part {part.id} is not watertight and solid")
                else:
                    exports.append(str(target))
        (export_dir / "parts_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {
            "pass": not failures, "failures": failures,
            "failure_codes": ["EXPORT_CONTRACT_FAILURE"] if failures else [],
            "exports": exports, "manifest": manifest,
        }

    def validate_ir(self, ir: MechanicalSystemIR | None) -> dict:
        if ir is None or not ir.is_assembly:
            return {"pass": True, "failures": [], "failure_codes": [], "estimated_dof": 0}

        failures = []
        codes = []
        ids = [p.id for p in ir.parts]
        idset = set(ids)
        if len(ids) != len(idset):
            failures.append("Mechanical IR contains duplicate part IDs")
            codes.append("ASSEMBLY_STRUCTURE_FAILURE")
        if len(ir.parts) < 2:
            failures.append("Mechanical assembly must contain at least two parts")
            codes.append("ASSEMBLY_STRUCTURE_FAILURE")
        grounded = [p.id for p in ir.parts if p.grounded]
        if len(grounded) != 1:
            failures.append(f"Mechanical assembly requires exactly one grounded part; found {len(grounded)}")
            codes.append("ASSEMBLY_STRUCTURE_FAILURE")

        adjacency = {pid: set() for pid in idset}
        estimated_dof = 0
        for j in ir.joints:
            if j.type not in ALLOWED_JOINTS:
                failures.append(f"Joint {j.id} has unsupported type {j.type}")
                codes.append("JOINT_CONSTRAINT_FAILURE")
            if j.parent not in idset or j.child not in idset:
                failures.append(f"Joint {j.id} references unknown part")
                codes.append("ASSEMBLY_STRUCTURE_FAILURE")
                continue
            if j.parent == j.child:
                failures.append(f"Joint {j.id} connects a part to itself")
                codes.append("ASSEMBLY_STRUCTURE_FAILURE")
            adjacency[j.parent].add(j.child)
            adjacency[j.child].add(j.parent)
            if _norm(j.axis) < 0.9:
                failures.append(f"Joint {j.id} axis is zero or not normalized")
                codes.append("JOINT_CONSTRAINT_FAILURE")
            if j.type in MOVING_JOINTS:
                estimated_dof += 1
                if j.clearance_mm is None or j.clearance_mm < self.minimum_moving_clearance_mm:
                    failures.append(
                        f"Joint {j.id} clearance {j.clearance_mm} mm is below {self.minimum_moving_clearance_mm} mm"
                    )
                    codes.append("CLEARANCE_FAILURE")
                if j.limits is None or len(j.limits) != 2 or j.limits[0] >= j.limits[1]:
                    failures.append(f"Joint {j.id} requires increasing [min,max] limits")
                    codes.append("JOINT_CONSTRAINT_FAILURE")

        if idset:
            start = grounded[0] if grounded else next(iter(idset))
            seen = {start}
            stack = [start]
            while stack:
                node = stack.pop()
                for nxt in adjacency.get(node, ()):
                    if nxt not in seen:
                        seen.add(nxt); stack.append(nxt)
            if seen != idset:
                failures.append(f"Joint graph is disconnected; reached {len(seen)}/{len(idset)} parts")
                codes.append("ASSEMBLY_STRUCTURE_FAILURE")

        effective_dof = estimated_dof
        if ir.closed_loops:
            moving_joints = sum(j.type in MOVING_JOINTS for j in ir.joints)
            effective_dof = 3 * (len(ir.parts) - 1) - 2 * moving_joints
        if ir.expected_dof is not None and effective_dof != ir.expected_dof:
            failures.append(f"Expected {ir.expected_dof} DOF but joint graph defines {effective_dof}")
            codes.append("JOINT_CONSTRAINT_FAILURE")
        return {
            "pass": not failures,
            "failures": failures,
            "failure_codes": list(dict.fromkeys(codes)),
            "estimated_dof": effective_dof,
            "part_count": len(ir.parts),
            "joint_count": len(ir.joints),
            "grounded_parts": grounded,
        }

    def validate_mesh(self, stl_path: str | Path, ir: MechanicalSystemIR | None, export_dir: str | Path | None = None) -> dict:
        if ir is None or not ir.is_assembly:
            return {"pass": True, "failures": [], "failure_codes": [], "component_count": 1, "exports": []}
        mesh = trimesh.load_mesh(stl_path, process=True)
        if export_dir is not None and self._has_export_contract(ir):
            contract = self._export_contract_parts(Path(stl_path).with_suffix(".scad").resolve(), ir, Path(export_dir))
            return {
                "pass": contract["pass"], "failures": contract["failures"],
                "failure_codes": contract["failure_codes"],
                "component_count": len(mesh.split(only_watertight=False)),
                "expected_component_count": len(ir.parts), "component_matches": [],
                "exports": contract["exports"], "manifest": contract["manifest"],
            }
        comps = list(mesh.split(only_watertight=False))
        failures = []
        codes = []
        expected = len(ir.parts)
        if len(comps) != expected:
            failures.append(f"Expected {expected} distinct assembly parts but STL contains {len(comps)} components")
            codes.append("PART_COUNT_FAILURE")
        bad = []
        for i, comp in enumerate(comps):
            if not comp.is_watertight or abs(float(comp.volume)) <= 0:
                bad.append(i)
        if bad:
            failures.append(f"Assembly components not individually watertight/solid: {bad}")
            codes.append("PART_GEOMETRY_FAILURE")

        exports = []
        matches = []
        if len(comps) == expected:
            origins = np.array([p.origin_mm for p in ir.parts], dtype=float)
            centroids = np.array([c.centroid for c in comps], dtype=float)
            remaining = set(range(len(comps)))
            for pi, part in enumerate(ir.parts):
                ci = min(remaining, key=lambda idx: float(np.linalg.norm(centroids[idx] - origins[pi])))
                remaining.remove(ci)
                distance = float(np.linalg.norm(centroids[ci] - origins[pi]))
                matches.append({"part_id": part.id, "component_index": ci, "centroid_mm": centroids[ci].round(3).tolist(), "origin_distance_mm": round(distance, 3)})
                if export_dir is not None:
                    target_dir = Path(export_dir)
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target = target_dir / f"{part.id}.stl"
                    comps[ci].export(target)
                    exports.append(str(target))
        return {
            "pass": not failures,
            "failures": failures,
            "failure_codes": list(dict.fromkeys(codes)),
            "component_count": len(comps),
            "expected_component_count": expected,
            "component_matches": matches,
            "exports": exports,
        }
