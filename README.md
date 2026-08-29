# Text-to-CAD

A closed-loop, testable text-to-CAD research pipeline using Python as the bridge between human intent, LLM reasoning, parametric OpenSCAD, deterministic validation, repair, and printable output.

Current development line: **V4 Milestone 2 (`4.1.0-dev2`)**.

## Current pipeline

Human request -> knowledge retrieval -> planner -> engineering IR -> mechanical IR -> OpenSCAD generator -> real OpenSCAD -> STL + multi-view PNG -> geometry/manufacturing validation -> assembly validation -> sampled kinematics -> OpenSCAD mesh-intersection collision validation -> semantic critic -> targeted repair -> validated artifacts / reusable knowledge.

## V4 Milestone 2

V4 now validates mechanisms through sampled motion, not only at their nominal pose. It supports fixed, revolute, and prismatic joints, serial transform propagation, Cartesian sampling of multi-joint configurations, exact OpenSCAD interference tests on exported meshes, moving-clearance diagnostics, collision witness artifacts, and motion-specific repair routing.

The expanded offline benchmark is 9/9 passing and the explicitly rerun regression groups are 21/21 passing with real OpenSCAD 2021.01.

See `V4_MILESTONE_2_REPORT.md` for details and limitations.

## Execution modes

- `mock`: deterministic contextual JSON-backed LLM behavior for offline development.
- `replay`: replay previously recorded normalized LLM calls.
- `live`: use the OpenAI API when credentials are available.

All modes share the same orchestration, prompts, OpenSCAD execution, validators, logging, and repair loop.
