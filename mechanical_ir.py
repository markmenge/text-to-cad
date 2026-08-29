# Suggested filename: mechanical_ir.py

from dataclasses import asdict, dataclass, field

# pip install instructions:
# No third-party packages required.


@dataclass
class PartIR:
    id: str
    role: str
    origin_mm: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    grounded: bool = False
    printable: bool = True


@dataclass
class JointIR:
    id: str
    type: str
    parent: str
    child: str
    axis: list[float]
    origin_mm: list[float]
    limits: list[float] | None = None
    clearance_mm: float | None = None


@dataclass
class MechanicalSystemIR:
    parts: list[PartIR]
    joints: list[JointIR]
    expected_dof: int | None = None
    assembly_notes: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @property
    def is_assembly(self) -> bool:
        return len(self.parts) > 1 or bool(self.joints)


def derive_mechanical_ir(planner_data: dict) -> MechanicalSystemIR | None:
    raw = planner_data.get("mechanical_system")
    if not isinstance(raw, dict):
        return None
    parts = []
    for i, item in enumerate(raw.get("parts", []), 1):
        parts.append(PartIR(
            id=str(item.get("id") or f"part_{i}"),
            role=str(item.get("role") or item.get("id") or f"part_{i}"),
            origin_mm=[float(v) for v in item.get("origin_mm", [0, 0, 0])],
            grounded=bool(item.get("grounded", False)),
            printable=bool(item.get("printable", True)),
        ))
    joints = []
    for i, item in enumerate(raw.get("joints", []), 1):
        joints.append(JointIR(
            id=str(item.get("id") or f"joint_{i}"),
            type=str(item.get("type") or "fixed").lower(),
            parent=str(item.get("parent") or ""),
            child=str(item.get("child") or ""),
            axis=[float(v) for v in item.get("axis", [0, 0, 1])],
            origin_mm=[float(v) for v in item.get("origin_mm", [0, 0, 0])],
            limits=[float(v) for v in item["limits"]] if item.get("limits") is not None else None,
            clearance_mm=float(item["clearance_mm"]) if item.get("clearance_mm") is not None else None,
        ))
    return MechanicalSystemIR(
        parts=parts,
        joints=joints,
        expected_dof=int(raw["expected_dof"]) if raw.get("expected_dof") is not None else None,
        assembly_notes=[str(x) for x in raw.get("assembly_notes", [])],
    )
