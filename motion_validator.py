# Suggested filename: motion_validator.py

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh

from kinematics import motion_configurations, part_transforms
from mechanical_ir import MechanicalSystemIR

# pip install instructions:
# py -m pip install trimesh numpy


def _scad_matrix(T: np.ndarray) -> str:
    rows = []
    for row in T.tolist():
        rows.append("[" + ",".join(f"{float(v):.10g}" for v in row) + "]")
    return "[" + ",".join(rows) + "]"


def _aabb_overlap(mesh_a: trimesh.Trimesh, mesh_b: trimesh.Trimesh, tolerance: float = 1e-7) -> bool:
    a0, a1 = mesh_a.bounds
    b0, b1 = mesh_b.bounds
    return bool(np.all(a1 >= b0 - tolerance) and np.all(b1 >= a0 - tolerance))


def _sample_vertices(mesh: trimesh.Trimesh, limit: int = 400) -> np.ndarray:
    v = np.asarray(mesh.vertices)
    if len(v) <= limit:
        return v
    idx = np.linspace(0, len(v)-1, limit).round().astype(int)
    return v[idx]


def _approx_clearance(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    """Symmetric vertex-to-triangle distance; conservative enough for regression diagnostics."""
    try:
        pa = _sample_vertices(a)
        pb = _sample_vertices(b)
        _, da, _ = trimesh.proximity.closest_point_naive(b, pa)
        _, db, _ = trimesh.proximity.closest_point_naive(a, pb)
        return float(min(np.min(da), np.min(db)))
    except Exception:
        # AABB separation is still a useful lower-order fallback.
        a0, a1 = a.bounds
        b0, b1 = b.bounds
        sep = np.maximum(np.maximum(a0 - b1, b0 - a1), 0.0)
        return float(np.linalg.norm(sep))


class MotionCollisionValidator:
    """Sample joint configurations and use OpenSCAD intersection() for exact interference checks."""

    def __init__(self, openscad: str = "/usr/bin/openscad", samples_per_joint: int = 3, max_configurations: int = 27):
        self.openscad = openscad
        self.samples_per_joint = int(samples_per_joint)
        self.max_configurations = int(max_configurations)

    def _intersects(self, path_a: Path, path_b: Path, Ta: np.ndarray, Tb: np.ndarray, work: Path, stem: str, evidence_dir: Path | None = None) -> tuple[bool, dict]:
        scad = work / f"{stem}.scad"
        out = work / f"{stem}.stl"
        scad.write_text(
            "intersection(){\n"
            f"  multmatrix({_scad_matrix(Ta)}) import(\"{path_a.resolve().as_posix()}\");\n"
            f"  multmatrix({_scad_matrix(Tb)}) import(\"{path_b.resolve().as_posix()}\");\n"
            "}\n",
            encoding="ascii",
        )
        proc = subprocess.run([self.openscad, "-o", str(out), str(scad)], capture_output=True, text=True)
        combined = (proc.stdout or "") + (proc.stderr or "")
        empty = "Current top level object is empty" in combined or not out.exists() or out.stat().st_size == 0
        collision = not empty and proc.returncode == 0
        evidence = []
        if collision and evidence_dir is not None:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            scad_target = evidence_dir / f"{stem}.scad"
            stl_target = evidence_dir / f"{stem}.stl"
            shutil.copy2(scad, scad_target)
            shutil.copy2(out, stl_target)
            evidence = [str(scad_target), str(stl_target)]
        return collision, {
            "returncode": proc.returncode,
            "empty": empty,
            "evidence": evidence,
            "stderr_tail": combined[-1200:],
        }

    def validate(self, ir: MechanicalSystemIR | None, part_paths: dict[str, str | Path], evidence_dir: str | Path | None = None) -> dict:
        if ir is None or not ir.is_assembly:
            return {"pass": True, "failure_codes": [], "failures": [], "configurations": [], "collision_count": 0}
        missing = [p.id for p in ir.parts if p.id not in part_paths]
        if missing:
            return {
                "pass": False,
                "failure_codes": ["MOTION_VALIDATION_UNAVAILABLE"],
                "failures": [f"Missing exported part meshes for motion validation: {missing}"],
                "configurations": [],
                "collision_count": 0,
            }
        base_meshes = {pid: trimesh.load_mesh(str(path), process=True) for pid, path in part_paths.items()}
        configs = motion_configurations(ir, self.samples_per_joint, self.max_configurations)
        joint_by_pair = {(j.parent, j.child): j for j in ir.joints}
        joint_by_pair.update({(j.child, j.parent): j for j in ir.joints})
        failures = []
        codes = []
        config_results = []
        collision_count = 0
        min_clearance_seen = {}
        evidence_dir = Path(evidence_dir) if evidence_dir is not None else None
        with tempfile.TemporaryDirectory(prefix="text_to_cad_motion_") as td:
            work = Path(td)
            for ci, config in enumerate(configs):
                transforms = part_transforms(ir, config["joint_values"])
                moved = {}
                for pid, mesh in base_meshes.items():
                    m = mesh.copy()
                    m.apply_transform(transforms[pid])
                    moved[pid] = m
                pair_results = []
                ids = [p.id for p in ir.parts]
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        a, b = ids[i], ids[j]
                        ma, mb = moved[a], moved[b]
                        collision = False
                        exact = {"skipped_by_aabb": True}
                        if _aabb_overlap(ma, mb):
                            collision, exact = self._intersects(
                                Path(part_paths[a]), Path(part_paths[b]), transforms[a], transforms[b], work,
                                f"c{ci:03d}_{a}_{b}", evidence_dir=evidence_dir,
                            )
                        clearance = 0.0 if collision else _approx_clearance(ma, mb)
                        key = f"{a}|{b}"
                        min_clearance_seen[key] = min(clearance, min_clearance_seen.get(key, float("inf")))
                        joint = joint_by_pair.get((a, b))
                        required = float(joint.clearance_mm) if joint and joint.type in {"revolute", "prismatic"} and joint.clearance_mm is not None else None
                        clearance_fail = required is not None and not collision and clearance + 0.05 < required
                        pair_results.append({
                            "parts": [a, b], "collision": collision,
                            "approx_clearance_mm": round(float(clearance), 4),
                            "required_clearance_mm": required,
                            "clearance_fail": clearance_fail,
                            "exact": exact,
                        })
                        if collision:
                            collision_count += 1
                            codes.append("MOTION_COLLISION_FAILURE")
                            failures.append(f"Collision at {config['id']} between {a} and {b}; joint_values={config['joint_values']}")
                        if clearance_fail:
                            codes.append("MOTION_CLEARANCE_FAILURE")
                            failures.append(
                                f"Clearance at {config['id']} between {a} and {b} is about {clearance:.3f} mm, below requested {required:.3f} mm"
                            )
                config_results.append({
                    "configuration_id": config["id"],
                    "joint_values": config["joint_values"],
                    "pairs": pair_results,
                })
        return {
            "pass": not codes,
            "failure_codes": list(dict.fromkeys(codes)),
            "failures": list(dict.fromkeys(failures)),
            "sample_count": len(configs),
            "collision_count": collision_count,
            "minimum_pair_clearance_mm": {k: round(float(v), 4) for k, v in min_clearance_seen.items()},
            "configurations": config_results,
        }
