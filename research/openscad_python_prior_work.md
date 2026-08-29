# Recovered OpenSCAD / Python Prior Work

## Core conclusion
Choose the geometric representation before writing OpenSCAD.

## Closed-loop architecture
1. Natural-language prompt.
2. Planner creates a structured design brief.
3. Retrieve relevant CAD patterns only.
4. Generator writes parameterized OpenSCAD.
5. OpenSCAD exports STL and PNG.
6. Python validates mesh and render.
7. Critic reviews engineering metrics and image when available.
8. Repair only failed subsystems where possible.
9. Stop on PASS or attempt limit.

## Representation table
| Shape need | Better representation |
| --- | --- |
| Boxes, brackets, panels | CSG primitives and Boolean operations |
| Cups, vases, knobs | 2D profile plus rotate_extrude() |
| Aircraft fuselages, bodies, animals | hulls, ellipsoids, blended primitives |
| Gears, teeth, threads | library or formula-driven generator |
| Complex imported surfaces | STL / mesh workflow rather than pure OpenSCAD |

Broader strategies: primitive CSG, extrusion, revolve, sweep, loft/hull, shell, array/pattern, formula/library, mechanism skeleton, and imported meshes.

Examples: chess piece -> revolve; bracket -> 2D sketch/extrude/Boolean; bent tube -> sweep approximation; gearbox -> mechanism skeleton plus housing; aircraft -> fuselage stations plus wing/tail subsystems.

## Prompting and repair rules
- Use named parameters and modules.
- Use assertions for dimensions and clearances where useful.
- Use fixed camera views for repeatable render comparisons.
- Keep generator and critic roles separate.
- Freeze successful geometry rather than rewriting everything.
- Prefer targeted repairs once most geometry works.
- For FDM, intentionally overlap features that must become one component.
- Avoid fragile detached details on organic models.

## Validation metrics
- OpenSCAD compile succeeds.
- STL and PNG exist and are non-empty.
- Mesh is watertight.
- Mesh has one connected component unless multiple parts are intentional.
- Bounding box is near requested dimensions.
- Positive plausible volume and face count.
- PNG is nonblank and visually matches the request.

## RAG direction
Keep a small local corpus of successful patterns and lessons. Retrieve only the patterns relevant to the current design brief, then later store successful models and repair notes back into the corpus.
