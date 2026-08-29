# Suggested filename: manufacturing.py

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

# pip install instructions:
# No third-party packages required.


@dataclass
class ManufacturingProfile:
    name: str = "generic_fdm_0p4"
    process: str = "FDM"
    nozzle_mm: float = 0.4
    layer_height_mm: float = 0.2
    min_wall_mm: float = 0.8
    min_feature_mm: float = 0.4
    xy_clearance_mm: float = 0.3
    build_volume_mm: tuple[float, float, float] = (256.0, 256.0, 256.0)

    def to_dict(self):
        return asdict(self)


class ManufacturingValidator:
    """Deterministic envelope checks; optional external slicer discovery is explicit."""

    SLICER_NAMES = ("orca-slicer", "OrcaSlicer", "prusa-slicer", "PrusaSlicer", "cura-slicer", "cura")

    def __init__(self, profile: ManufacturingProfile | None = None):
        self.profile = profile or ManufacturingProfile()
        self.slicer = next((shutil.which(x) for x in self.SLICER_NAMES if shutil.which(x)), None)

    def validate_metrics(self, metrics: dict) -> dict:
        failures = []
        bbox = metrics.get("bbox_mm")
        if bbox:
            for axis, (actual, limit) in enumerate(zip(bbox, self.profile.build_volume_mm)):
                if actual > limit:
                    failures.append(f"axis {axis} size {actual} mm exceeds build volume {limit} mm")
            if min(bbox) < self.profile.min_feature_mm:
                failures.append(f"overall model thickness below nominal minimum feature {self.profile.min_feature_mm} mm")
        return {
            "pass": not failures,
            "profile": self.profile.to_dict(),
            "failures": failures,
            "slicer_available": bool(self.slicer),
            "slicer_executable": self.slicer,
            "scope": "manufacturing envelope only; wall-thickness/support validation requires a slicer or dedicated geometry analysis",
        }

    def write_profile(self, path: str | Path):
        Path(path).write_text(json.dumps(self.profile.to_dict(), indent=2), encoding="utf-8")
