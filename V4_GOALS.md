# Text-to-CAD V4 Goals

V4 extends dependable text-to-CAD from isolated printable objects toward mechanical systems.

## Primary Goals

1. Represent multiple physical parts explicitly rather than treating every prompt as a single STL body.
2. Represent fixed, revolute, and prismatic joints with stable part IDs, axes, origins, limits, and clearances.
3. Validate mechanical structure deterministically: unique parts, connected joint graph, one grounded reference, legal joint definitions, expected degrees of freedom, and minimum moving clearance.
4. Preserve V3 behavior and regression coverage for ordinary single-part CAD.
5. Export validated assembly components as separate named STL files.
6. Sample declared joint motion so motion semantics become inspectable and testable data.
7. Add mechanical benchmarks that deliberately exercise repair loops rather than only happy paths.
8. Keep all mechanical decisions logged and reproducible in the existing run bundle.

## V4 Dev1 Definition of Success

V4 dev1 is successful when the existing five shape benchmarks continue to pass, new revolute and prismatic mechanism benchmarks pass through real OpenSCAD, deliberately merged moving parts are detected and repaired, joint/DOF/clearance errors are caught offline, and successful assemblies produce separate part STL exports plus motion samples.

## Milestone 2 - Motion Validation

1. Transform actual exported part meshes through declared joint travel.
2. Detect interference with exact solid intersection, not only bounding boxes.
3. Validate moving clearances through sampled configurations.
4. Preserve collision witness geometry for post-run failure analysis.
5. Propagate transforms through serial joint chains.
6. Sample multi-joint Cartesian configurations so combined-pose collisions are testable.
7. Route motion failures back into targeted repair.
8. Add at least one two-DOF mechanical benchmark while preserving all previous shape and one-DOF regressions.
