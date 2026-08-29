# Suggested filename: llm_client.py

import base64
import hashlib
import json
import mimetypes
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# pip install instructions:
# Optional online mode: py -m pip install openai


@dataclass
class LLMRequest:
    role: str
    prompt: str
    context: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    fixture_id: str | None = None
    metadata: dict[str, Any] | None = None


class PromptLibrary:
    def __init__(self, prompt_dir: str | Path):
        self.prompt_dir = Path(prompt_dir)
        self.common = (self.prompt_dir / "text-to-cad.md").read_text(encoding="ascii")
        self.stage = {
            role: (self.prompt_dir / f"{role}.md").read_text(encoding="ascii")
            for role in ("planner", "generator", "critic")
        }

    def hashes(self) -> dict[str, str]:
        result = {}
        for path in [self.prompt_dir / "text-to-cad.md"] + [self.prompt_dir / f"{r}.md" for r in ("planner", "generator", "critic")]:
            result[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return result

    def assemble(self, request: LLMRequest) -> str:
        runtime = {
            "user_prompt": request.prompt,
            "context": request.context,
        }
        return (
            self.common.rstrip()
            + "\n\n"
            + self.stage[request.role].rstrip()
            + "\n\n# Runtime Request\n"
            + json.dumps(runtime, indent=2, sort_keys=True, ensure_ascii=True)
            + "\n"
        )


class LLMClient:
    def __init__(self, prompt_dir: str | Path):
        self.prompt_library = PromptLibrary(prompt_dir)
        self.trace: list[dict[str, Any]] = []
        self.last_assembled_prompt = ""

    def _record(self, request: LLMRequest, response: LLMResponse, assembled: str, elapsed_s: float, provider: str):
        self.last_assembled_prompt = assembled
        self.trace.append({
            "role": request.role,
            "prompt": request.prompt,
            "context": request.context,
            "assembled_prompt": assembled,
            "response_text": response.text,
            "fixture_id": response.fixture_id,
            "metadata": response.metadata or {},
            "provider": provider,
            "elapsed_s": round(elapsed_s, 6),
        })

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class MockOpenAIClient(LLMClient):
    """Deterministic contextual offline replacement for OpenAI."""

    def __init__(self, fixture_path: str | Path, prompt_dir: str | Path | None = None):
        fixture_path = Path(fixture_path)
        prompt_dir = Path(prompt_dir) if prompt_dir else fixture_path.parent.parent / "prompts"
        super().__init__(prompt_dir)
        self.fixture_path = fixture_path
        data = json.loads(self.fixture_path.read_text(encoding="ascii"))
        self.rules = data["rules"]
        self.defaults = data.get("defaults", {})

    @staticmethod
    def _contains_all(text: str, needles: list[str]) -> bool:
        low = text.lower()
        return all(n.lower() in low for n in needles)

    def _match(self, rule: dict[str, Any], request: LLMRequest) -> tuple[bool, int]:
        m = rule.get("match", {})
        score = 0
        if "role" in m:
            if request.role != m["role"]:
                return False, 0
            score += 100
        items = m.get("prompt_contains", [])
        if items:
            if not self._contains_all(request.prompt, items):
                return False, 0
            score += 10 * len(items)
        object_type = m.get("object_type")
        if object_type is not None:
            if request.context.get("object_type") != object_type:
                return False, 0
            score += 50
        iteration = int(request.context.get("iteration", 1))
        if "iteration_min" in m:
            if iteration < int(m["iteration_min"]):
                return False, 0
            score += 8
        if "iteration_max" in m:
            if iteration > int(m["iteration_max"]):
                return False, 0
            score += 8
        feedback = "\n".join(request.context.get("feedback", []))
        items = m.get("feedback_contains", [])
        if items:
            if not self._contains_all(feedback, items):
                return False, 0
            score += 12 * len(items)
        strategies = request.context.get("strategies", [])
        options = m.get("strategy_any", [])
        if options:
            if not any(s in strategies for s in options):
                return False, 0
            score += 6
        return True, score

    def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        assembled = self.prompt_library.assemble(request)
        candidates = []
        for index, rule in enumerate(self.rules):
            matched, score = self._match(rule, request)
            if matched:
                candidates.append((score, -index, rule))
        if not candidates:
            default = self.defaults.get(request.role)
            if default is None:
                raise LookupError(f"No mock fixture matched role={request.role!r}")
            response = LLMResponse(text=default, fixture_id="default", metadata={"mode": "mock"})
        else:
            _, _, rule = max(candidates, key=lambda x: (x[0], x[1]))
            raw = rule["response"]
            if isinstance(raw, dict):
                response = LLMResponse(text=raw.get("text", ""), fixture_id=rule.get("id"), metadata=raw.get("metadata") or {"mode": "mock"})
            else:
                response = LLMResponse(text=raw, fixture_id=rule.get("id"), metadata={"mode": "mock"})
        self._record(request, response, assembled, time.perf_counter() - start, "mock")
        return response


def _request_key(request: LLMRequest) -> str:
    # Normalize volatile filesystem locations so a cassette can replay in a
    # different run directory or on another machine. Image content is input
    # evidence, but its absolute path is not part of the semantic request.
    data = asdict(request)
    context = dict(data.get("context", {}))
    if "image_paths" in context:
        context["image_paths"] = [Path(p).name for p in context.get("image_paths", [])]
    data["context"] = context
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


class ReplayClient(LLMClient):
    """Replay responses previously recorded from a live client."""

    def __init__(self, cassette_path: str | Path, prompt_dir: str | Path):
        super().__init__(prompt_dir)
        self.cassette_path = Path(cassette_path)
        data = json.loads(self.cassette_path.read_text(encoding="utf-8"))
        calls = data.get("calls", data if isinstance(data, list) else [])
        self.recorded_prompt_hashes = data.get("prompt_hashes", {}) if isinstance(data, dict) else {}
        self.prompt_hash_mismatch = bool(self.recorded_prompt_hashes and self.recorded_prompt_hashes != self.prompt_library.hashes())
        self.by_key = {c["request_key"]: c for c in calls}

    def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        assembled = self.prompt_library.assemble(request)
        key = _request_key(request)
        if key not in self.by_key:
            raise LookupError(f"Replay cassette has no response for request {key[:12]} role={request.role}")
        call = self.by_key[key]
        response = LLMResponse(
            text=call["response_text"],
            fixture_id=call.get("fixture_id") or f"replay:{key[:12]}",
            metadata={"mode": "replay", "source_metadata": call.get("metadata", {}), "prompt_hash_mismatch": self.prompt_hash_mismatch},
        )
        self._record(request, response, assembled, time.perf_counter() - start, "replay")
        return response


class OpenAIClient(LLMClient):
    def __init__(self, prompt_dir: str | Path, model: str | None = None, cassette_path: str | Path | None = None):
        from openai import OpenAI
        super().__init__(prompt_dir)
        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_CAD_MODEL", "gpt-5.6")
        self.cassette_path = Path(cassette_path) if cassette_path else None
        self._cassette_calls: list[dict[str, Any]] = []

    @staticmethod
    def _image_part(path: str | Path) -> dict[str, Any]:
        path = Path(path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"type": "input_image", "image_url": f"data:{mime};base64,{data}"}

    def _save_cassette(self):
        if not self.cassette_path:
            return
        self.cassette_path.parent.mkdir(parents=True, exist_ok=True)
        self.cassette_path.write_text(json.dumps({"prompt_hashes": self.prompt_library.hashes(), "calls": self._cassette_calls}, indent=2), encoding="utf-8")

    def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()
        assembled = self.prompt_library.assemble(request)
        input_parts: list[dict[str, Any]] = [{"type": "input_text", "text": assembled}]
        if request.role == "critic":
            for image_path in request.context.get("image_paths", []):
                if Path(image_path).exists():
                    input_parts.append(self._image_part(image_path))
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "high"},
            input=[{"role": "user", "content": input_parts}],
        )
        metadata = {
            "mode": "live",
            "model": self.model,
            "response_id": getattr(response, "id", None),
            "usage": getattr(getattr(response, "usage", None), "model_dump", lambda: {})(),
        }
        result = LLMResponse(text=response.output_text.strip(), fixture_id=None, metadata=metadata)
        self._record(request, result, assembled, time.perf_counter() - start, "openai")
        self._cassette_calls.append({
            "request_key": _request_key(request),
            "role": request.role,
            "request": asdict(request),
            "response_text": result.text,
            "metadata": metadata,
        })
        self._save_cassette()
        return result
