# Suggested filename: pipeline_v3.py

import json
from dataclasses import asdict
from pathlib import Path

from llm_client import LLMRequest
from pipeline_v2 import (
    Brief, CADController, DeterministicValidator, LLMGenerator, OpenSCADCompiler,
    Requirement, _normalize_requirements, _sha256, create_llm,
)
from engineering_ir import derive_ir
from knowledge_capture import capture_success
from manufacturing import ManufacturingProfile, ManufacturingValidator
from retrieval import CorpusRetriever
from version import PIPELINE_VERSION

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional online mode: py -m pip install openai


class KnowledgeAwarePlanner:
    def __init__(self, llm, retriever: CorpusRetriever, manufacturing_profile: ManufacturingProfile):
        self.llm = llm
        self.retriever = retriever
        self.manufacturing_profile = manufacturing_profile
        self.last_retrieved = []
        self.last_ir = None
        self.last_raw = None

    def plan(self, prompt: str):
        self.last_retrieved = self.retriever.search(prompt, limit=3)
        context = {
            "retrieved_patterns": self.retriever.serializable(self.last_retrieved),
            "manufacturing_profile": self.manufacturing_profile.to_dict(),
        }
        response = self.llm.generate(LLMRequest(role="planner", prompt=prompt, context=context))
        data = json.loads(response.text)
        self.last_raw = data
        brief = Brief(
            prompt=prompt,
            object_type=data["object_type"],
            strategies=list(data.get("strategies", [])),
            dimensions_mm=data.get("dimensions_mm"),
            requirements=_normalize_requirements(data.get("requirements")),
        )
        self.last_ir = derive_ir(prompt, data, [x.path for x in self.last_retrieved])
        return brief, response.fixture_id


class IRAwareGenerator(LLMGenerator):
    def __init__(self, llm, planner: KnowledgeAwarePlanner):
        super().__init__(llm)
        self.planner = planner

    def generate(self, brief: Brief, feedback: list[str], failure_codes: list[str], repair_route: str, iteration: int):
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
            "retrieved_patterns": self.planner.retriever.serializable(self.planner.last_retrieved),
            "manufacturing_profile": self.planner.manufacturing_profile.to_dict(),
        }
        response = self.llm.generate(LLMRequest(role="generator", prompt=brief.prompt, context=context))
        text = response.text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1])
        return text + "\n", response.fixture_id


class V3Validator(DeterministicValidator):
    def __init__(self, manufacturing: ManufacturingValidator):
        super().__init__()
        self.manufacturing = manufacturing
        self.last_manufacturing = None

    def validate(self, brief: Brief, build):
        passed, reasons, codes, metrics, reqs = super().validate(brief, build)
        self.last_manufacturing = self.manufacturing.validate_metrics(metrics)
        metrics["manufacturing"] = self.last_manufacturing
        if not self.last_manufacturing["pass"]:
            passed = False
            if "PRINTABILITY_FAILURE" not in codes:
                codes.append("PRINTABILITY_FAILURE")
            reasons.extend(self.last_manufacturing["failures"])
        return passed, reasons, codes, metrics, reqs


class V3CADController(CADController):
    def __init__(self, llm, root: Path, max_iterations: int = 3, profile: ManufacturingProfile | None = None):
        self.root = root
        self.manufacturing_profile = profile or ManufacturingProfile()
        self.retriever = CorpusRetriever([root / "corpus" / "patterns", root / "research", root / "knowledge" / "successes"])
        planner = KnowledgeAwarePlanner(llm, self.retriever, self.manufacturing_profile)
        super().__init__(llm, max_iterations=max_iterations)
        self.planner = planner
        self.generator = IRAwareGenerator(llm, planner)
        self.manufacturing = ManufacturingValidator(self.manufacturing_profile)
        self.validator = V3Validator(self.manufacturing)

    def _run_metadata(self, prompt: str, mode: str, run_id: str):
        data = super()._run_metadata(prompt, mode, run_id)
        data["pipeline_version"] = PIPELINE_VERSION
        data["v3_features"] = [
            "offline_corpus_retrieval", "engineering_ir", "manufacturing_profile",
            "manufacturing_envelope_validation", "successful_run_knowledge_capture",
        ]
        data["manufacturing_profile"] = self.manufacturing_profile.to_dict()
        data["slicer_available"] = bool(self.manufacturing.slicer)
        return data

    def run(self, prompt: str, out: Path, mode: str = "mock"):
        report = super().run(prompt, out, mode=mode)
        retrieved = self.retriever.serializable(self.planner.last_retrieved)
        ir = self.planner.last_ir.to_dict() if self.planner.last_ir else {}
        (out / "retrieval_context.json").write_text(json.dumps(retrieved, indent=2), encoding="utf-8")
        (out / "engineering_ir.json").write_text(json.dumps(ir, indent=2), encoding="utf-8")
        (out / "manufacturing_profile.json").write_text(json.dumps(self.manufacturing_profile.to_dict(), indent=2), encoding="utf-8")
        if report.get("passed"):
            knowledge_path = capture_success(self.root, report, ir, retrieved)
            report["knowledge_capture"] = str(knowledge_path.relative_to(self.root)) if knowledge_path else None
            (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report


def run_one_v3(prompt: str, out: Path, mode: str = "mock", max_iterations: int = 3, cassette: Path | None = None):
    root = Path(__file__).resolve().parent
    controller = V3CADController(create_llm(mode, root, cassette), root=root, max_iterations=max_iterations)
    return controller.run(prompt, out, mode=mode)
