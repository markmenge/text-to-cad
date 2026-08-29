# Text-to-CAD V4 Milestone 1 Report

## Status

V4 dev1 extends the V3 shape pipeline into an initial mechanical-system pipeline while preserving the existing single-part path.

OpenSCAD execution was verified at `/usr/bin/openscad`, version 2021.01. All CAD integration cases below were compiled and rendered with the real OpenSCAD executable.

## Implemented

### Mechanical intermediate representation

V4 adds explicit physical parts and joints. Mechanical parts have stable IDs, roles, nominal origins, grounded/printable state. Joints currently support fixed, revolute, and prismatic relationships with parent/child references, normalized axes, origins, limits, and manufacturing clearance.

### Deterministic mechanical validation

The offline validator now checks:

- unique part IDs
- exactly one grounded reference for a simple mechanism
- legal joint types
- valid parent/child references
- no self-joints
- connected joint graph
- normalized joint axes
- increasing motion limits
- minimum moving-part clearance
- expected versus declared degrees of freedom
- expected physical part count in the compiled STL
- individual watertight/positive-volume mesh components

### Multi-body CAD semantics

Single printable parts retain the V3 rule requiring one connected mesh. Mechanical assemblies are different: moving parts are expected to remain separate mesh components. This distinction prevents assembly support from weakening normal single-part validation.

### Named part export

When the number of STL components matches the mechanical IR, components are matched to declared part origins and exported as named STL files. The V4 hinge produces `base.stl` and `lid.stl`; the slider produces `guide.stl` and `slider.stl`.

### Kinematic sampling

Revolute and prismatic joint transforms are sampled at their declared limits and midpoint and recorded as `motion_samples.json`. This is an inspectable foundation for later motion-envelope and collision testing.

### Mechanical prompting and knowledge

The planner, generator, critic, and common prompt context now explicitly describe mechanical systems. New retrieval patterns cover revolute hinges and prismatic sliders.

## Regression Results

The V4 controller passed all seven current integration benchmarks:

| Case | Result | Iterations | Purpose |
| --- | --- | ---: | --- |
| Cube | PASS | 1 | Preserve primitive single-part behavior |
| Pepper name tag | PASS | 1 | Preserve dimensions/text/Boolean behavior |
| Frog in teacup | PASS | 2 | Preserve semantic/manufacturing repair |
| Bishop | PASS | 1 | Preserve revolve/Boolean behavior |
| F-16 | PASS | 2 | Preserve connectivity repair |
| Revolute hinge demonstrator | PASS | 2 | Detect merged moving parts, repair, export parts, sample motion |
| Prismatic slider demonstrator | PASS | 2 | Detect merged moving parts, repair, export parts, sample motion |

Result: **7/7 V4 integration benchmarks pass**. First-pass success is 3/7 because four cases intentionally exercise repair behavior. Average iterations: 1.571.

The legacy and feature tests were run in split groups because the combined multi-view frog render exceeds the execution-call timeout. Across the split runs, the existing mock/prompt, V2 observability/replay, V3 retrieval/IR/manufacturing, offline repair, and new V4 mechanical tests all pass. The V4-specific test module is 5/5.

## Important Bugs Found During V4 Development

The first hinge repair looked plausible in a perspective render but the lid tube intersected the base body. Real mesh validation correctly continued to report a single component. The fixture was redesigned so the base axle sits inside a clearance bore in the lid while supports remain outside the lid tube. Only then was the benchmark accepted.

This is a useful example of why semantic appearance alone is not sufficient for mechanical CAD.

## Current Limitations

V4 dev1 does not yet prove that a mechanism can move through its full range without collision. `motion_samples.json` currently validates and records kinematic transforms but does not transform the actual meshes and perform swept-volume/collision analysis.

Part-to-component identity is currently inferred from nominal part origins and mesh centroids. More complex assemblies will need explicit per-part generation/export contracts.

There is no installed slicer in this sandbox, so slicer-level printability remains an optional backend rather than a claimed validation step.

Live LLM mechanical quality is not certified because this execution environment has no API key. Mock fixtures test orchestration and fault recovery, not foundation-model intelligence.

## Recommended V4 Milestone 2

1. Transform actual part meshes through sampled joint states and add collision/interference testing.
2. Add a per-part generation contract so every declared part has explicit source and STL identity rather than centroid matching.
3. Add assembly configurations and exploded views.
4. Add fastener, shaft/bearing, gear-pair, and snap/press-fit interface primitives to the mechanical IR.
5. Add tolerance-stack and fit-class concepts.
6. Add at least one two-joint mechanism benchmark, such as a four-bar linkage or crank-slider.
7. Add live-model qualification once API access is available.

V4 dev1 is therefore a tested mechanical-system foundation, not a claim that arbitrary mechanisms are solved.
