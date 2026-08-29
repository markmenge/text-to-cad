# Benchmark Test Report

Environment:
- OpenSCAD: /usr/bin/openscad
- OpenSCAD version: 2021.01
- Headless PNG rendering: xvfb-run
- Mesh validation: trimesh

## Results

| Benchmark | Strategy | Result | Bounding box mm | Watertight | Components |
| --- | --- | --- | --- | --- | --- |
| Cube | primitive CSG | PASS | 20 x 20 x 20 | yes | 1 |
| Pepper tag | 2D extrusion + Boolean + text | PASS | 60 x 20 x 2 | yes | 1 |
| Frog in teacup | shell + organic hull | PASS | 72 x 56 x 57.196 | yes | 1 |
| Bishop | revolve + Boolean | PASS | 44 x 44 x 70.995 | yes | 1 |
| F-16 | hull/loft + symmetry + subsystems | PASS after geometry fix | 111.981 x 68 x 33.978 | yes | 1 |

The initial F-16 test failed because the wings were on a Z plane that did not intersect the fuselage. The validator correctly reported a non-watertight mesh with three connected components. Moving the wings into the fuselage plane fixed the defect; the full suite then passed 5/5.

## What is tested now
- Strategy classification for the five benchmark classes.
- Real OpenSCAD STL compilation.
- Real OpenSCAD PNG rendering.
- Watertightness.
- Connected components.
- Bounding box.
- Explicit dimensional tolerance for cube and name tag.
- Positive volume and face count.
- Nonblank render check.

## What still needs API testing
- LLM planner instead of deterministic keyword planning.
- LLM OpenSCAD generation for all five prompts.
- Multimodal visual semantic critic using the PNG.
- Repair loop driven by critic feedback.
- Retrieval quality evaluation against a larger RAG corpus.
