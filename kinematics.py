# Suggested filename: kinematics.py

import itertools
import math

import numpy as np

from mechanical_ir import MechanicalSystemIR

# pip install instructions:
# py -m pip install numpy


def _axis_angle(axis, angle_rad):
    axis = np.array(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s, C = math.cos(angle_rad), math.sin(angle_rad), 1 - math.cos(angle_rad)
    return np.array([
        [x*x*C+c, x*y*C-z*s, x*z*C+y*s],
        [y*x*C+z*s, y*y*C+c, y*z*C-x*s],
        [z*x*C-y*s, z*y*C+x*s, z*z*C+c],
    ])


def joint_transform(joint, value):
    """Relative motion from the nominal (value=0) assembly pose."""
    T = np.eye(4)
    axis = np.array(joint.axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    if joint.type == "prismatic":
        T[:3, 3] = axis * float(value)
    elif joint.type == "revolute":
        origin = np.array(joint.origin_mm, dtype=float)
        R = _axis_angle(axis, math.radians(float(value)))
        T[:3, :3] = R
        T[:3, 3] = origin - R @ origin
    return T


def nominal_joint_value(joint) -> float:
    if not joint.limits:
        return 0.0
    lo, hi = [float(v) for v in joint.limits]
    if lo <= 0.0 <= hi:
        return 0.0
    return lo if abs(lo) <= abs(hi) else hi


def motion_configurations(ir: MechanicalSystemIR | None, samples_per_joint: int = 3, max_configurations: int = 27) -> list[dict]:
    """Return deterministic Cartesian motion samples for all moving joints."""
    if ir is None:
        return []
    moving = [j for j in ir.joints if j.type in {"revolute", "prismatic"} and j.limits]
    if ir.closed_loops:
        drivers = {str(loop.get("input_joint")) for loop in ir.closed_loops if loop.get("input_joint")}
        moving = [j for j in moving if j.id in drivers]
    if not moving:
        return [{"id": "nominal", "joint_values": {}}]
    sample_sets = []
    for joint in moving:
        lo, hi = [float(v) for v in joint.limits]
        if samples_per_joint <= 1:
            vals = [nominal_joint_value(joint)]
        else:
            vals = np.linspace(lo, hi, samples_per_joint).tolist()
            nominal = nominal_joint_value(joint)
            if samples_per_joint >= 3 and all(abs(v - nominal) > 1e-9 for v in vals):
                vals[len(vals)//2] = nominal
        sample_sets.append([round(float(v), 6) for v in vals])
    combos = list(itertools.product(*sample_sets))
    if len(combos) > max_configurations:
        # Keep deterministic coverage of the configuration sequence including endpoints.
        indexes = np.linspace(0, len(combos)-1, max_configurations).round().astype(int)
        combos = [combos[i] for i in dict.fromkeys(indexes.tolist())]
    results = []
    for idx, combo in enumerate(combos):
        values = {j.id: v for j, v in zip(moving, combo)}
        results.append({"id": f"cfg_{idx:03d}", "joint_values": values})
    return results


def part_transforms(ir: MechanicalSystemIR | None, joint_values: dict[str, float] | None = None) -> dict[str, np.ndarray]:
    """Propagate transforms from the grounded part through a tree-like joint graph."""
    if ir is None:
        return {}
    joint_values = joint_values or {}
    if ir.closed_loops:
        return _closed_loop_transforms(ir, joint_values)
    transforms = {p.id: np.eye(4) for p in ir.parts if p.grounded}
    unresolved = list(ir.joints)
    # Fixed and moving joints are both parent->child relationships.
    for _ in range(len(ir.parts) + len(ir.joints) + 2):
        if not unresolved:
            break
        next_unresolved = []
        progress = False
        for joint in unresolved:
            if joint.parent not in transforms:
                next_unresolved.append(joint)
                continue
            value = float(joint_values.get(joint.id, nominal_joint_value(joint)))
            transforms[joint.child] = transforms[joint.parent] @ joint_transform(joint, value)
            progress = True
        unresolved = next_unresolved
        if not progress:
            break
    for p in ir.parts:
        transforms.setdefault(p.id, np.eye(4))
    return transforms


def _rigid_2d(angle: float, translation: np.ndarray) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    T = np.eye(4)
    T[:2, :2] = [[c, -s], [s, c]]
    T[:2, 3] = translation[:2]
    return T


def _rotation_about(point: np.ndarray, angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array([[c, -s], [s, c]])
    return _rigid_2d(angle, point - rotation @ point)


def _circle_intersections(center_a: np.ndarray, radius_a: float, center_b: np.ndarray, radius_b: float, branch: int) -> tuple[np.ndarray, np.ndarray]:
    delta = center_b - center_a
    distance = float(np.linalg.norm(delta))
    if distance == 0 or distance > radius_a + radius_b or distance < abs(radius_a - radius_b):
        raise ValueError("Four-bar link lengths do not close for the requested input angle")
    unit = delta / distance
    along = (radius_a * radius_a - radius_b * radius_b + distance * distance) / (2 * distance)
    height = math.sqrt(max(radius_a * radius_a - along * along, 0.0))
    midpoint = center_a + along * unit
    perpendicular = np.array([-unit[1], unit[0]])
    first = midpoint + height * perpendicular
    second = midpoint - height * perpendicular
    return first, second


def _closed_loop_transforms(ir: MechanicalSystemIR, joint_values: dict[str, float]) -> dict[str, np.ndarray]:
    transforms = {p.id: np.eye(4) for p in ir.parts if p.grounded}
    for loop in ir.closed_loops:
        if loop.get("type") != "four_bar":
            continue
        names = loop.get("parts", {})
        lengths = loop.get("link_lengths_mm", {})
        pivots = np.array(loop.get("ground_pivots_mm", [[0, 0], [80, 0]]), dtype=float)
        ground_a, ground_d = pivots[0], pivots[1]
        input_joint = str(loop["input_joint"])
        input_value = float(joint_values.get(input_joint, loop.get("nominal_input_deg", 0.0)))
        crank_nominal = float(loop.get("nominal_input_deg", 0.0))
        crank_length = float(lengths["crank"])
        coupler_length = float(lengths["coupler"])
        rocker_length = float(lengths["rocker"])
        branch = 1 if int(loop.get("branch", 1)) >= 0 else -1

        def solve(angle_deg: float) -> tuple[np.ndarray, np.ndarray]:
            theta = math.radians(angle_deg)
            crank_end = ground_a + crank_length * np.array([math.cos(theta), math.sin(theta)])
            candidates = _circle_intersections(crank_end, coupler_length, ground_d, rocker_length, branch)
            coupler_end = candidates[0] if branch >= 0 else candidates[1]
            return crank_end, coupler_end

        nominal_crank_end, nominal_coupler_end = solve(crank_nominal)
        crank_end, coupler_end = solve(input_value)
        nominal_crank_angle = math.atan2(*(nominal_crank_end - ground_a)[::-1])
        current_crank_angle = math.atan2(*(crank_end - ground_a)[::-1])
        transforms[names["crank"]] = _rotation_about(ground_a, current_crank_angle - nominal_crank_angle)

        nominal_coupler_vector = nominal_coupler_end - nominal_crank_end
        current_coupler_vector = coupler_end - crank_end
        coupler_rotation = math.atan2(current_coupler_vector[1], current_coupler_vector[0]) - math.atan2(nominal_coupler_vector[1], nominal_coupler_vector[0])
        transforms[names["coupler"]] = _rigid_2d(coupler_rotation, crank_end - _rigid_2d(coupler_rotation, np.zeros(2))[:2, :2] @ nominal_crank_end)

        nominal_rocker_vector = nominal_coupler_end - ground_d
        current_rocker_vector = coupler_end - ground_d
        rocker_rotation = math.atan2(current_rocker_vector[1], current_rocker_vector[0]) - math.atan2(nominal_rocker_vector[1], nominal_rocker_vector[0])
        transforms[names["rocker"]] = _rigid_2d(rocker_rotation, ground_d - _rigid_2d(rocker_rotation, np.zeros(2))[:2, :2] @ ground_d)
    for p in ir.parts:
        transforms.setdefault(p.id, np.eye(4))
    return transforms


def sample_motion(ir: MechanicalSystemIR | None, samples_per_joint: int = 3) -> list[dict]:
    """Backward-compatible per-joint motion samples used by V4 dev1 reports."""
    if ir is None:
        return []
    results = []
    for joint in ir.joints:
        if joint.type not in {"revolute", "prismatic"} or not joint.limits:
            continue
        lo, hi = joint.limits
        values = np.linspace(lo, hi, samples_per_joint)
        for value in values:
            T = joint_transform(joint, float(value))
            results.append({
                "joint_id": joint.id,
                "joint_type": joint.type,
                "value": round(float(value), 5),
                "transform": np.round(T, 6).tolist(),
            })
    return results
