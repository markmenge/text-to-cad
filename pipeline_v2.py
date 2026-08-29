# Suggested filename: pipeline_v2.py

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageStat

from llm_client import LLMClient, LLMRequest, MockOpenAIClient, OpenAIClient, ReplayClient
from version import PIPELINE_VERSION

# pip install instructions:
# py -m pip install trimesh pillow numpy
# Optional online mode: py -m pip install openai


FAILURE_TYPES = {
    "PLAN_FAILURE",
    "SCAD_SYNTAX_FAILURE",
    "OPENSCAD_COMPILE_FAILURE",
    "EMPTY_MODEL",
    "DIMENSION_FAILURE",
    "DISCONNECTED_COMPONENTS",
    "NON_MANIFOLD",
    "FEATURE_MISSING",
    "SEMANTIC_MISMATCH",
    "PRINTABILITY_FAILURE",
    "REPAIR_REGRESSION",
    "RETRY_EXHAUSTED",
    "PIPELINE_INTERNAL_ERROR",
}


@dataclass
class Requirement:
    id: str
    type: str
    text: str


@dataclass
class Brief:
    prompt: str
    object_type: str
    strategies: list[str]
    dimensions_mm: list[float] | None
    requirements: list[Requirement]


@dataclass
class BuildResult:
    scad_path: str
    stl_path: str
    image_paths: list[str]
    stl_rc: int
    stl_stdout: str
    stl_stderr: str
    render_results: list[dict]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _requirement_type(text: str) -> str:
    low = text.lower()
    if any(x in low for x in (" mm", "cm", "dimension", "size", "diameter", "thick", "offset")):
        return "dimension"
    if "text" in low or "pepper" in low or "hole" in low or "slot" in low:
        return "feature"
    if any(x in low for x in ("connected", "watertight", "printable", "manifold")):
        return "manufacturing"
    if any(x in low for x in ("symmetr", "fuselage", "wing", "frog", "cup", "bishop")):
        return "semantic"
    return "geometry"


def _normalize_requirements(raw: list | None) -> list[Requirement]:
    result = []
    for i, item in enumerate(raw or [], 1):
        if isinstance(item, dict):
            result.append(Requirement(
                id=str(item.get("id") or f"R{i}"),
                type=str(item.get("type") or _requirement_type(str(item.get("text", "")))),
                text=str(item.get("text", "")),
            ))
        else:
            text = str(item)
            result.append(Requirement(id=f"R{i}", type=_requirement_type(text), text=text))
    if not any(r.type == "manufacturing" and "connected" in r.text.lower() for r in result):
        result.append(Requirement(id=f"R{len(result)+1}", type="manufacturing", text="One connected printable object"))
    return result


class LLMPlanner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, prompt: str) -> tuple[Brief, str | None]:
        response = self.llm.generate(LLMRequest(role="planner", prompt=prompt, context={}))
        data = json.loads(response.text)
        brief = Brief(
            prompt=prompt,
            object_type=data["object_type"],
            strategies=list(data.get("strategies", [])),
            dimensions_mm=data.get("dimensions_mm"),
            requirements=_normalize_requirements(data.get("requirements")),
        )
        return brief, response.fixture_id


class LLMGenerator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

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
        }
        response = self.llm.generate(LLMRequest(role="generator", prompt=brief.prompt, context=context))
        text = response.text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1])
        return text + "\n", response.fixture_id


class OpenSCADCompiler:
    def __init__(self):
        candidates = (
            [r"C:\Program Files\OpenSCAD\openscad.com", r"C:\Program Files\OpenSCAD\openscad.exe"]
            if os.name == "nt" else ["/usr/bin/openscad"]
        )
        self.exe = next((x for x in candidates if Path(x).exists()), None)
        if not self.exe:
            raise FileNotFoundError("Required OpenSCAD executable not found")
        version = subprocess.run([self.exe, "--version"], capture_output=True, text=True)
        self.version = (version.stdout or version.stderr).strip()

    def _run_render(self, scad_path: Path, png_path: Path, camera: str | None, projection: str):
        cmd = [self.exe, "-o", str(png_path), "--imgsize=600,480", "--viewall", "--autocenter", f"--projection={projection}"]
        if camera:
            cmd += [f"--camera={camera}"]
        cmd.append(str(scad_path))
        if os.name != "nt" and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a"] + cmd
        r = subprocess.run(cmd, capture_output=True, text=True)
        return {"name": png_path.stem, "command": cmd, "returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}

    def build(self, scad: str, out: Path) -> BuildResult:
        out.mkdir(parents=True, exist_ok=True)
        scad_path = out / "model.scad"
        stl_path = out / "model.stl"
        scad_path.write_text(scad, encoding="ascii", errors="strict")
        stl_cmd = [self.exe, "-o", str(stl_path), str(scad_path)]
        (out / "openscad_stl_command.json").write_text(json.dumps(stl_cmd, indent=2), encoding="utf-8")
        stl_result = subprocess.run(stl_cmd, capture_output=True, text=True)
        (out / "openscad_stl_stdout.txt").write_text(stl_result.stdout, encoding="utf-8")
        (out / "openscad_stl_stderr.txt").write_text(stl_result.stderr, encoding="utf-8")

        views = [
            ("perspective", None, "perspective"),
            ("front", "0,0,0,90,0,0,100", "orthogonal"),
            ("side", "0,0,0,90,0,90,100", "orthogonal"),
            ("top", "0,0,0,0,0,0,100", "orthogonal"),
        ]
        render_results = []
        image_paths = []
        if stl_result.returncode == 0:
            jobs = [(name, camera, projection, out / f"view_{name}.png") for name, camera, projection in views]
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [(path, pool.submit(self._run_render, scad_path, path, camera, projection)) for name, camera, projection, path in jobs]
                for path, future in futures:
                    rr = future.result()
                    render_results.append(rr)
                    if rr["returncode"] == 0 and path.exists() and path.stat().st_size:
                        image_paths.append(str(path))
        (out / "render_results.json").write_text(json.dumps(render_results, indent=2), encoding="utf-8")
        return BuildResult(
            scad_path=str(scad_path), stl_path=str(stl_path), image_paths=image_paths,
            stl_rc=stl_result.returncode, stl_stdout=stl_result.stdout, stl_stderr=stl_result.stderr,
            render_results=render_results,
        )


class DeterministicValidator:
    def validate(self, brief: Brief, build: BuildResult):
        reasons: list[str] = []
        codes: list[str] = []
        metrics = {"stl_rc": build.stl_rc, "render_count": len(build.image_paths)}
        stl = Path(build.stl_path)
        if build.stl_rc:
            codes.append("OPENSCAD_COMPILE_FAILURE")
            reasons.append("OpenSCAD STL compile failed")
            if "Parser error" in build.stl_stderr or "syntax error" in build.stl_stderr.lower():
                codes.append("SCAD_SYNTAX_FAILURE")
        if not stl.exists() or not stl.stat().st_size:
            codes.append("EMPTY_MODEL")
            reasons.append("STL missing or empty")
        if len(build.image_paths) < 4 and build.stl_rc == 0:
            reasons.append(f"Only {len(build.image_paths)}/4 render views succeeded")
        if codes:
            return False, reasons, list(dict.fromkeys(codes)), metrics, self._requirement_results(brief, False, codes)

        mesh = trimesh.load_mesh(stl, process=True)
        components = len(mesh.split(only_watertight=False))
        metrics.update(
            watertight=bool(mesh.is_watertight), components=components, faces=int(len(mesh.faces)),
            vertices=int(len(mesh.vertices)), volume_mm3=round(float(abs(mesh.volume)), 3),
            bbox_mm=[round(float(v), 3) for v in mesh.extents],
            z_min_mm=round(float(mesh.bounds[0][2]), 3), z_max_mm=round(float(mesh.bounds[1][2]), 3),
        )
        if not mesh.is_watertight:
            codes.append("NON_MANIFOLD"); reasons.append("mesh not watertight")
        if components != 1:
            codes.append("DISCONNECTED_COMPONENTS"); reasons.append(f"connected components={components}")
        if metrics["volume_mm3"] <= 0:
            codes.append("EMPTY_MODEL"); reasons.append("non-positive volume")
        if brief.dimensions_mm:
            error = np.abs(np.array(mesh.extents) - np.array(brief.dimensions_mm))
            metrics["dimension_error_mm"] = [round(float(v), 3) for v in error]
            if np.any(error > 0.25):
                codes.append("DIMENSION_FAILURE"); reasons.append("explicit dimensions outside 0.25 mm tolerance")
        if metrics["z_min_mm"] < -0.05:
            codes.append("PRINTABILITY_FAILURE"); reasons.append("model extends below Z=0 print plane")
        image_stats = []
        for path in build.image_paths:
            stat = ImageStat.Stat(Image.open(path).convert("L"))
            image_stats.append(round(float(stat.stddev[0]), 3))
        metrics["render_stddev"] = image_stats
        if image_stats and max(image_stats) < 2:
            codes.append("EMPTY_MODEL"); reasons.append("all renders appear blank")
        return not codes, reasons, list(dict.fromkeys(codes)), metrics, self._requirement_results(brief, not codes, codes)

    def _requirement_results(self, brief: Brief, det_pass: bool, codes: list[str]):
        results = []
        for req in brief.requirements:
            status = "UNKNOWN"
            evidence = "Requires semantic critic"
            if req.type == "manufacturing" and "connected" in req.text.lower():
                status = "FAIL" if "DISCONNECTED_COMPONENTS" in codes else ("PASS" if det_pass else "UNKNOWN")
                evidence = "Mesh connected-component validation"
            elif req.type == "dimension" and brief.dimensions_mm:
                status = "FAIL" if "DIMENSION_FAILURE" in codes else ("PASS" if det_pass else "UNKNOWN")
                evidence = "Overall STL bounding-box validation"
            results.append({"id": req.id, "type": req.type, "text": req.text, "status": status, "evidence": evidence})
        return results


class LLMCritic:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def critique(self, brief: Brief, scad: str, metrics: dict, deterministic_feedback: list[str], requirement_results: list[dict], image_paths: list[str], iteration: int):
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
        }
        response = self.llm.generate(LLMRequest(role="critic", prompt=brief.prompt, context=context))
        data = json.loads(response.text)
        return bool(data["pass"]), int(data["score"]), list(data.get("feedback", [])), data.get("requirement_results", []), response.fixture_id


def repair_route(codes: list[str], semantic_feedback: list[str]) -> str:
    if "SCAD_SYNTAX_FAILURE" in codes or "OPENSCAD_COMPILE_FAILURE" in codes:
        return "syntax_compile_repair"
    if "DIMENSION_FAILURE" in codes:
        return "dimensional_repair"
    if "DISCONNECTED_COMPONENTS" in codes or "NON_MANIFOLD" in codes:
        return "connectivity_mesh_repair"
    if "MOTION_COLLISION_FAILURE" in codes or "MOTION_CLEARANCE_FAILURE" in codes:
        return "kinematic_interference_repair"
    if "PART_COUNT_FAILURE" in codes or "ASSEMBLY_STRUCTURE_FAILURE" in codes or "JOINT_CONSTRAINT_FAILURE" in codes:
        return "assembly_constraint_repair"
    if "CLEARANCE_FAILURE" in codes:
        return "mechanical_clearance_repair"
    if "PRINTABILITY_FAILURE" in codes:
        return "manufacturing_repair"
    if semantic_feedback:
        return "semantic_feature_repair"
    return "general_repair"


def classify_semantic_failure(sem_pass: bool, feedback: list[str]) -> list[str]:
    if sem_pass:
        return []
    low = " ".join(feedback).lower()
    result = []
    if any(x in low for x in ("missing", "text", "hole", "feature")):
        result.append("FEATURE_MISSING")
    if any(x in low for x in ("thin", "print", "support", "wall", "bottom")):
        result.append("PRINTABILITY_FAILURE")
    if not result:
        result.append("SEMANTIC_MISMATCH")
    return result


class CADController:
    def __init__(self, llm: LLMClient, max_iterations: int = 3):
        self.llm = llm
        self.planner = LLMPlanner(llm)
        self.generator = LLMGenerator(llm)
        self.compiler = OpenSCADCompiler()
        self.validator = DeterministicValidator()
        self.critic = LLMCritic(llm)
        self.max_iterations = max_iterations

    def _run_metadata(self, prompt: str, mode: str, run_id: str):
        root = Path(__file__).resolve().parent
        artifact_hashes = {}
        for rel in ("mocks/mock_openai.json", "research/modeling_strategies.md", "research/openscad_python_prior_work.md"):
            path = root / rel
            if path.exists():
                artifact_hashes[rel] = _sha256(path)
        cassette = getattr(self.llm, "cassette_path", None)
        if cassette and Path(cassette).exists():
            artifact_hashes["cassette"] = _sha256(Path(cassette))
        return {
            "run_id": run_id, "pipeline_version": PIPELINE_VERSION, "mode": mode,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(), "prompt": prompt,
            "python_version": sys.version.split()[0], "platform": platform.platform(),
            "openscad_executable": self.compiler.exe, "openscad_version": self.compiler.version,
            "llm_client": type(self.llm).__name__, "llm_model": getattr(self.llm, "model", None),
            "prompt_hashes": self.llm.prompt_library.hashes(), "artifact_hashes": artifact_hashes,
            "max_iterations": self.max_iterations,
        }

    def run(self, prompt: str, out: Path, mode: str = "mock"):
        start = time.perf_counter()
        out.mkdir(parents=True, exist_ok=True)
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        metadata = self._run_metadata(prompt, mode, run_id)
        (out / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        (out / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
        history = []
        feedback: list[str] = []
        failure_codes: list[str] = []
        route = "initial_generation"
        try:
            brief, planner_fixture = self.planner.plan(prompt)
            (out / "planner_brief.json").write_text(json.dumps({**asdict(brief), "requirements": [asdict(r) for r in brief.requirements]}, indent=2), encoding="utf-8")
            self._write_trace(out / "planner_call.json", self.llm.trace[-1])
        except Exception as exc:
            report = self._fatal_report(prompt, metadata, "PLAN_FAILURE", str(exc), start)
            self._finish(out, report)
            return report

        prior_metrics = None
        for iteration in range(1, self.max_iterations + 1):
            idir = out / f"iteration_{iteration:02d}"
            idir.mkdir(parents=True, exist_ok=True)
            try:
                scad, gen_fixture = self.generator.generate(brief, feedback, failure_codes, route, iteration)
                self._write_trace(idir / "generator_call.json", self.llm.trace[-1])
                build = self.compiler.build(scad, idir)
                det_pass, det_feedback, det_codes, metrics, req_results = self.validator.validate(brief, build)
                (idir / "validator.json").write_text(json.dumps({"pass": det_pass, "feedback": det_feedback, "failure_codes": det_codes, "metrics": metrics, "requirement_results": req_results}, indent=2), encoding="utf-8")
                sem_pass, score, sem_feedback, semantic_req_results, critic_fixture = self.critic.critique(
                    brief, scad, metrics, det_feedback, req_results, build.image_paths, iteration
                )
                self._write_trace(idir / "critic_call.json", self.llm.trace[-1])
                sem_codes = classify_semantic_failure(sem_pass, sem_feedback)
                combined_codes = list(dict.fromkeys(det_codes + sem_codes))
                combined_feedback = list(dict.fromkeys(det_feedback + sem_feedback))
                merged_req = self._merge_requirement_results(req_results, semantic_req_results, sem_pass)
                final_pass = det_pass and sem_pass
                regression = False
                if prior_metrics and not final_pass and iteration > 1:
                    regression = self._is_regression(prior_metrics, metrics, det_codes)
                    if regression:
                        combined_codes.append("REPAIR_REGRESSION")
                record = {
                    "iteration": iteration, "planner_fixture": planner_fixture, "generator_fixture": gen_fixture,
                    "critic_fixture": critic_fixture, "deterministic_pass": det_pass, "semantic_pass": sem_pass,
                    "final_pass": final_pass, "score": score, "failure_codes": combined_codes,
                    "feedback": combined_feedback, "repair_route": route, "metrics": metrics,
                    "requirement_results": merged_req, "image_paths": [str(Path(p).relative_to(out)) for p in build.image_paths],
                    "regression_detected": regression,
                }
                history.append(record)
                (idir / "iteration_summary.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
                if final_pass:
                    self._copy_final(out, build)
                    break
                feedback = combined_feedback
                failure_codes = combined_codes
                route = repair_route(combined_codes, sem_feedback)
                prior_metrics = metrics
            except Exception as exc:
                failure_codes = ["PIPELINE_INTERNAL_ERROR"]
                feedback = [f"Internal pipeline error: {exc}"]
                history.append({"iteration": iteration, "final_pass": False, "failure_codes": failure_codes, "feedback": feedback, "repair_route": route, "score": 0, "requirement_results": []})
                break

        passed = bool(history and history[-1].get("final_pass"))
        final_codes = [] if passed else list(dict.fromkeys(history[-1].get("failure_codes", []) + (["RETRY_EXHAUSTED"] if len(history) >= self.max_iterations else [])))
        report = {
            **metadata, "brief": {**asdict(brief), "requirements": [asdict(r) for r in brief.requirements]},
            "passed": passed, "iterations": history, "final_failure_codes": final_codes,
            "elapsed_s": round(time.perf_counter() - start, 3),
        }
        report["metrics_summary"] = self._metrics_summary(history)
        self._finish(out, report)
        return report

    @staticmethod
    def _write_trace(path: Path, trace: dict):
        path.write_text(json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8")

    @staticmethod
    def _merge_requirement_results(det: list[dict], semantic: list[dict], sem_pass: bool):
        by_id = {r["id"]: dict(r) for r in det}
        for r in semantic or []:
            if r.get("id") in by_id:
                by_id[r["id"]].update(r)
        if not semantic and sem_pass:
            for r in by_id.values():
                if r["status"] == "UNKNOWN" and r["type"] in ("semantic", "feature", "geometry"):
                    r["status"] = "PASS"; r["evidence"] = "Semantic critic overall pass"
        return list(by_id.values())

    @staticmethod
    def _is_regression(prior: dict, current: dict, codes: list[str]):
        if "OPENSCAD_COMPILE_FAILURE" in codes:
            return True
        if prior.get("components") == 1 and current.get("components", 1) > 1:
            return True
        if prior.get("watertight") is True and current.get("watertight") is False:
            return True
        return False

    @staticmethod
    def _metrics_summary(history: list[dict]):
        return {
            "iterations": len(history),
            "final_score": history[-1].get("score", 0) if history else 0,
            "first_pass_success": bool(history and history[0].get("final_pass")),
            "repair_count": max(0, len(history) - 1),
        }

    @staticmethod
    def _copy_final(out: Path, build: BuildResult):
        final = out / "final"
        final.mkdir(exist_ok=True)
        shutil.copy2(build.scad_path, final / "model.scad")
        shutil.copy2(build.stl_path, final / "model.stl")
        for p in build.image_paths:
            shutil.copy2(p, final / Path(p).name)

    @staticmethod
    def _fatal_report(prompt: str, metadata: dict, code: str, error: str, start: float):
        return {**metadata, "prompt": prompt, "passed": False, "iterations": [], "final_failure_codes": [code], "error": error, "elapsed_s": round(time.perf_counter() - start, 3)}

    def _finish(self, out: Path, report: dict):
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._write_postmortem(out, report)

    @staticmethod
    def _write_postmortem(out: Path, report: dict):
        lines = ["# Text-to-CAD Run Postmortem", "", f"- Run ID: {report.get('run_id')}", f"- Result: {'PASS' if report.get('passed') else 'FAIL'}", f"- Prompt: {report.get('prompt')}", f"- Iterations: {len(report.get('iterations', []))}", f"- Elapsed: {report.get('elapsed_s', 0)} s", ""]
        if report.get("passed"):
            lines += ["## Outcome", "", "The run satisfied deterministic validation and semantic critique.", ""]
        else:
            lines += ["## Final failure classification", ""]
            for code in report.get("final_failure_codes", []):
                lines.append(f"- {code}")
            lines += ["", "## Iteration history", ""]
            for it in report.get("iterations", []):
                lines.append(f"### Iteration {it.get('iteration')}")
                lines.append(f"- Repair route: {it.get('repair_route')}")
                lines.append(f"- Score: {it.get('score')}")
                lines.append(f"- Failure codes: {', '.join(it.get('failure_codes', [])) or 'none'}")
                for fb in it.get("feedback", []):
                    lines.append(f"- Feedback: {fb}")
                lines.append("")
            lines += ["## Likely next action", "", "Inspect the last failed requirement and failure code, then update the relevant planner, generator, critic, validator, or repair-route behavior.", ""]
        codes = report.get("final_failure_codes", [])
        root_cause_map = {
            "PLAN_FAILURE": "Planner response could not be converted into a usable CAD brief.",
            "SCAD_SYNTAX_FAILURE": "Generated OpenSCAD contains invalid syntax.",
            "OPENSCAD_COMPILE_FAILURE": "OpenSCAD could not compile the generated model.",
            "EMPTY_MODEL": "Compilation produced no usable solid/render output.",
            "DIMENSION_FAILURE": "The STL bounding box violates explicit dimensional requirements.",
            "DISCONNECTED_COMPONENTS": "The intended printable object contains disconnected mesh components.",
            "NON_MANIFOLD": "The generated mesh is not watertight/manifold.",
            "FEATURE_MISSING": "Semantic critique found a requested feature missing or incorrect.",
            "SEMANTIC_MISMATCH": "The render does not adequately represent the requested object.",
            "PRINTABILITY_FAILURE": "The model has an identified manufacturing/printability risk.",
            "REPAIR_REGRESSION": "A repair attempt damaged a property that previously validated.",
            "RETRY_EXHAUSTED": "The repair loop reached its configured attempt limit.",
            "PIPELINE_INTERNAL_ERROR": "The orchestration code encountered an internal exception.",
        }
        likely = next((root_cause_map[c] for c in codes if c != "RETRY_EXHAUSTED" and c in root_cause_map), "No failure remains; run passed." if report.get("passed") else "Failure requires manual inspection.")
        analysis = {
            "run_id": report.get("run_id"), "passed": report.get("passed"),
            "failure_codes": codes, "likely_root_cause": likely,
            "failed_requirements": [r for r in (report.get("iterations", [{}])[-1].get("requirement_results", []) if report.get("iterations") else []) if r.get("status") == "FAIL"],
            "iteration_count": len(report.get("iterations", [])),
            "recommended_next_action": "Inspect the last failed requirement/failure code and update the matching stage or repair route." if not report.get("passed") else "No repair action required.",
        }
        (out / "failure_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        if not report.get("passed"):
            lines += ["## Likely root cause", "", likely, ""]
        (out / "postmortem.md").write_text("\n".join(lines), encoding="ascii", errors="replace")


def create_llm(mode: str, root: Path, cassette: Path | None = None) -> LLMClient:
    prompt_dir = root / "prompts"
    if mode == "mock":
        return MockOpenAIClient(root / "mocks" / "mock_openai.json", prompt_dir)
    if mode == "replay":
        if not cassette:
            raise ValueError("Replay mode requires cassette path")
        return ReplayClient(cassette, prompt_dir)
    if mode == "openai":
        return OpenAIClient(prompt_dir, cassette_path=cassette)
    raise ValueError(f"Unknown LLM mode: {mode}")


def run_one(prompt: str, out: Path, mode: str = "mock", max_iterations: int = 3, cassette: Path | None = None):
    root = Path(__file__).resolve().parent
    controller = CADController(create_llm(mode, root, cassette), max_iterations=max_iterations)
    return controller.run(prompt, out, mode=mode)
