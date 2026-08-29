# Text-to-CAD v2 Completion Report

## Status

Implementation status: COMPLETE for offline/mock/replay engineering validation.
Live OpenAI statistical certification: NOT RUN because this execution sandbox has no OPENAI_API_KEY.

Pipeline version: 2.0.0
OpenSCAD requirement: real OpenSCAD executable is mandatory; this sandbox uses /usr/bin/openscad.

## Implemented v2 goals

- Versioned common/stage prompt files: text-to-cad.md, planner.md, generator.md, critic.md.
- Stable requirement ledger with R1/R2/... IDs and PASS/FAIL/UNKNOWN evidence.
- Four-view rendering: perspective, front, side, top.
- Deterministic OpenSCAD/STL validation: build result, nonempty geometry, watertightness, connected components, positive volume, explicit bounding-box dimensions, Z print-plane sanity, render sanity.
- Structured failure codes and repair routing.
- Per-iteration LLM request/response logging with exact assembled prompt.
- Per-iteration OpenSCAD command, stdout, stderr, STL, views, validator result, critic result, and summary.
- Run-level metadata including pipeline version, prompt hashes, research/mock hashes, Python/platform/OpenSCAD versions, LLM client/model, timing.
- Automatic report.json, postmortem.md, and failure_analysis.json.
- Mock, replay, and live OpenAI client modes use the same orchestration and prompt assembly.
- Live calls can record cassettes; replay normalizes volatile image filesystem paths.
- Cassette prompt hashes are stored so prompt-version mismatch can be detected.
- Regression benchmark runner reports success rate, first-pass rate, average iterations, elapsed time, and failure distribution.
- Fault injection covers compiler repair and retry exhaustion.

## Current offline benchmark result

Five standard benchmark prompts were run individually through the current v2 pipeline using contextual mock LLM responses and real OpenSCAD execution.

| Benchmark | Result | Iterations | Final score | Watertight | Components |
| --- | --- | ---: | ---: | --- | ---: |
| Cube | PASS | 1 | 95 | yes | 1 |
| Pepper name tag | PASS | 1 | 95 | yes | 1 |
| Frog in teacup | PASS | 2 | 95 | yes | 1 |
| Bishop | PASS | 1 | 95 | yes | 1 |
| F-16 | PASS | 2 | 95 | yes | 1 |

Aggregate: 5/5 PASS, 100% success, 60% first-pass success, 1.4 average iterations.

The frog repair path is driven by semantic/printability critic feedback. The F-16 repair path is driven by deterministic disconnected-component feedback.

## Replay validation

A cube run was converted into a cassette and replayed end-to-end through the full pipeline. Result: PASS.

A replay bug was discovered and fixed during testing: absolute render image paths originally changed request hashes between run directories. Replay request hashing now normalizes image paths to file names.

## Failure-analysis validation

A permanent syntax/compile failure was run with max_iterations=2. The pipeline stopped rather than looping forever and produced:

- OPENSCAD_COMPILE_FAILURE
- SCAD_SYNTAX_FAILURE
- EMPTY_MODEL
- REPAIR_REGRESSION
- RETRY_EXHAUSTED

The failed run also emitted a structured failure_analysis.json and human-readable postmortem.md.

## Definition of v2 completion

The v2 software release is considered complete when the orchestration and observability features above are implemented and pass offline regression testing. That criterion is met.

A separate LIVE CERTIFICATION remains intentionally outstanding. It requires an API key and should run repeated real-model generations (recommended: at least 20 per benchmark) to measure model intelligence rather than pipeline correctness. Those results should not be mocked or inferred.

## Recommended next command on Windows

Mock regression:

    py run_benchmarks_v2.py --llm mock

Live run with cassette recording:

    set OPENAI_API_KEY=...
    set OPENAI_CAD_MODEL=gpt-5.6
    py run_benchmarks_v2.py --llm openai --cassette cassettes\live_run.json

Replay recorded behavior:

    py run_benchmarks_v2.py --llm replay --cassette cassettes\live_run.json

