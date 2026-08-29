# Suggested filename: engineering_ir.py

from dataclasses import asdict, dataclass, field

# pip install instructions:
# No third-party packages required.


@dataclass
class Constraint:
    kind: str
    description: str
    value: object | None = None


@dataclass
class EngineeringIR:
    object_type: str
    primary_strategy: str
    secondary_strategies: list[str] = field(default_factory=list)
    subsystems: list[str] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    symmetry: str | None = None
    manufacturing_process: str = "FDM"
    retrieved_patterns: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def derive_ir(prompt: str, planner_data: dict, retrieved_paths: list[str]) -> EngineeringIR:
    strategies = list(planner_data.get("strategies", []))
    primary = planner_data.get("primary_strategy") or (strategies[0] if strategies else "primitive_csg")
    secondary = planner_data.get("secondary_strategies") or strategies[1:]
    object_type = str(planner_data.get("object_type", "object"))
    subsystems = list(planner_data.get("subsystems", []))
    symmetry = planner_data.get("symmetry")

    if not subsystems:
        defaults = {
            "name_tag": ["tag_body", "text", "keyring_hole"],
            "frog_teacup": ["cup_shell", "handle", "frog_body", "frog_head", "frog_limbs"],
            "bishop": ["base", "stem", "collar", "head", "mitre_slot"],
            "f16": ["fuselage", "nose", "wings", "tail", "vertical_stabilizer"],
            "cube": ["body"],
        }
        subsystems = defaults.get(object_type, ["body"])
    if symmetry is None:
        if object_type in {"bishop", "cup"}:
            symmetry = "radial"
        elif object_type in {"f16", "name_tag"}:
            symmetry = "bilateral"

    constraints = []
    dims = planner_data.get("dimensions_mm")
    if dims:
        constraints.append(Constraint("overall_dimensions", "Overall bounding box", dims))
    for req in planner_data.get("requirements", []):
        text = req.get("text", "") if isinstance(req, dict) else str(req)
        constraints.append(Constraint("requirement", text))
    manufacturing = planner_data.get("manufacturing") or {}
    process = manufacturing.get("process", "FDM") if isinstance(manufacturing, dict) else "FDM"
    return EngineeringIR(
        object_type=object_type,
        primary_strategy=primary,
        secondary_strategies=secondary,
        subsystems=subsystems,
        constraints=constraints,
        symmetry=symmetry,
        manufacturing_process=process,
        retrieved_patterns=retrieved_paths,
    )
