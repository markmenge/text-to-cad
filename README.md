# Text-to-CAD

A closed-loop, testable text-to-CAD research pipeline using Python as the bridge between human intent, LLM reasoning, parametric OpenSCAD, deterministic validation, repair, and printable output.

Current development line: **V4 Milestone 3 foundation (`4.1.0-dev2`)**.

## Current pipeline

Human request -> knowledge retrieval -> planner -> engineering IR -> mechanical IR -> OpenSCAD generator -> real OpenSCAD -> STL + multi-view PNG -> geometry/manufacturing validation -> assembly validation -> sampled kinematics -> OpenSCAD mesh-intersection collision validation -> semantic critic -> targeted repair -> validated artifacts / reusable knowledge.

## V4 Milestone 2

V4 now validates mechanisms through sampled motion, not only at their nominal pose. It supports fixed, revolute, and prismatic joints, serial transform propagation, Cartesian sampling of multi-joint configurations, exact OpenSCAD interference tests on exported meshes, moving-clearance diagnostics, collision witness artifacts, and motion-specific repair routing.

The expanded offline benchmark is 9/9 passing, the current offline regression suite is 31/31 passing, and the four-bar case passes through explicit part exports and closed-loop motion validation with real OpenSCAD 2021.01.

See `V4_MILESTONE_2_REPORT.md` for details and limitations.

## Execution modes

- `mock`: deterministic contextual JSON-backed LLM behavior for offline development.
- `replay`: replay previously recorded normalized LLM calls.
- `live`: use the OpenAI API when credentials are available.

All modes share the same orchestration, prompts, OpenSCAD execution, validators, logging, and repair loop.

## Getting started

### Prerequisites

- Python 3.11 or newer
- OpenSCAD 2021.01 or newer on `PATH`, or installed at the standard Windows location `C:\Program Files\OpenSCAD\openscad.com`
- An OpenAI API key only for `live` mode
- Optional slicer software for slicer-level printability checks; the current pipeline does not require or invoke one

Install the Python dependencies:

```text
py -m pip install -r requirements.txt
```

On Debian/Ubuntu, install OpenSCAD with `sudo apt install openscad`. On Windows, install OpenSCAD from the official desktop installer.

### Run an offline example

```text
py -m unittest discover -s tests -v
py run_v4_m2_benchmarks.py 01_cube
```

### Run a live example

Set `OPENAI_API_KEY` in the shell, then run:

```text
py -c "from pathlib import Path; from pipeline_v4 import run_one_v4; run_one_v4('Generate a 2 cm by 2 cm by 2 cm cube.', Path('runs/live_cube'), 'live')"
```

Live calls incur API usage. Run bundles contain the generated OpenSCAD source, STL, renders, validation metrics, prompts, and iteration history.

## Example output

This live-generated king example passed in one iteration with a score of 96. Its measured envelope was `22 x 22 x 47.495 mm`, and the STL was watertight with one connected volumetric solid.

![Live-generated king chess piece](king_view_perspective.png)

The full local evidence bundle is retained under `runs/live_king_475` when the example is run from this workspace; generated run bundles are intentionally excluded from source control.

## Capabilities and boundaries

The project is a tested research pipeline, not a general-purpose CAD system. It currently demonstrates:

- Deterministic mock and replay testing of planning, generation, repair, and artifact promotion
- Live OpenAI-backed generation through the same controller
- Parametric OpenSCAD output with STL and multi-view rendering
- Deterministic mesh checks for dimensions, watertightness, connectivity, build envelope, and volumetric hollow solids
- Mechanical IR for parts and fixed, revolute, and prismatic joints
- Sampled serial motion and a planar four-bar closure demonstrator
- Exact sampled mesh-intersection checks for mechanical interference

It does not yet guarantee continuous collision-free motion between samples, exact wall-thickness compliance from a slicer, support generation, material or strength analysis, dynamics, tolerance stacks, or high quality on arbitrary unseen live prompts. The manufacturing validator currently checks the build envelope and reports whether a slicer is available; it does not perform slicing.

## Publish milestone

The repository is ready for a first private GitHub release when these items are complete:

- `requirements.txt` and documented Python/OpenSCAD prerequisites
- A clean README with offline, replay, and live usage examples
- A reproducible offline regression result and at least one recorded live example
- No credentials or generated run bundles committed accidentally
- A tagged release or milestone commit with known limitations documented

The current repository satisfies the first four items. A future public release should add a recorded live cassette, broader unseen-prompt evaluation, and a slicer-backed printability check.
