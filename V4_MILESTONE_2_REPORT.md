# Text-to-CAD V4 Milestone 2 Report

## Status

V4 Milestone 2 is implemented and passing offline regression tests with real Debian OpenSCAD 2021.01.

Pipeline version: `4.1.0-dev2`

Milestone 2 moves mechanical validation from static assembly structure to sampled physical motion.

## Implemented

### Mesh-based motion validation

Validated assembly components are exported as named STL files. For each sampled joint configuration, the pipeline propagates part transforms from the grounded part through the parent-child joint tree.

For any pair whose transformed axis-aligned bounds overlap, the validator asks OpenSCAD to calculate the true solid intersection of the two transformed STL files. A nonempty intersection is a deterministic collision.

This intentionally uses the same OpenSCAD/CGAL geometry toolchain already trusted by the CAD pipeline rather than silently falling back to a coarse bounding-box collision test.

### Moving clearance checks

When no collision is present, a symmetric vertex-to-surface estimate is used to check the declared moving clearance between joint-connected parts. Collision decisions do not rely on this approximation; OpenSCAD intersection is authoritative for interference.

### Collision evidence

When a collision is detected, the iteration run bundle preserves:

- the exact OpenSCAD intersection source
- the collision/interference STL volume
- sampled joint values
- the affected part IDs
- OpenSCAD return/log evidence

This makes motion failures inspectable after the run.

### Kinematic convention

- The generated assembly is the zero-value nominal pose.
- Joint axes and origins are expressed in the parent part's nominal coordinate frame.
- Downstream parts inherit parent transforms before their own joint transform.
- If zero is outside legal limits, the nearest legal value is used as the nominal sample.

### Cartesian multi-joint sampling

A two-joint system with three samples per joint produces nine combined configurations. This is intentionally different from checking each joint separately; collisions caused only by combinations of joint values can now be detected.

### Repair routing

New deterministic failure routes include:

- `MOTION_COLLISION_FAILURE` -> `kinematic_interference_repair`
- `MOTION_CLEARANCE_FAILURE` -> `kinematic_interference_repair`
- assembly/part-count failures -> `assembly_constraint_repair`
- mechanical clearance failures -> `mechanical_clearance_repair`

Motion failures therefore enter the same closed repair loop as compile, geometry, semantic, and manufacturing failures.

## Important defect found by Milestone 2

The original V4 hinge passed nominal mesh validation, but the declared revolute joint origin was at Z=10 mm while the modeled axle center was at Z=9 mm. Once the lid was transformed through its legal range, the one-millimeter kinematic mismatch produced interference.

The motion validator exposed this hidden defect. The mechanical IR fixture was corrected to the true modeled axis and the hinge then validated through its full sampled travel with approximately 0.5 mm minimum clearance.

This is a concrete example of why nominal assembly validation alone is insufficient.

## New regression mechanisms

### Motion-collision repair demonstrator

The initial two-part model is valid and separate at the nominal pose, but the arm intersects the base at 45 and 90 degrees.

Iteration 1 detects `MOTION_COLLISION_FAILURE` and preserves collision witness STLs. The repair iteration moves the arm geometry to the collision-free side of the same declared joint. Iteration 2 passes all three sampled positions.

### Two-joint serial arm

Three physical parts:

- base
- arm1
- arm2

Two revolute joints and two expected degrees of freedom. Three values are sampled for each joint, producing nine Cartesian configurations. The final model passes all nine configurations with zero detected intersections. Minimum measured moving clearances are approximately 0.499 mm at both shaft/bore interfaces.

## Automated regression results

Core regression groups:

- V4 Milestone 2 motion tests: 3/3 PASS
- Existing V4 mechanical tests: 5/5 PASS
- Mock/prompt and V3 tests: 10/10 PASS
- V2 observability/replay tests: 3/3 PASS

Total explicitly rerun tests: **21/21 PASS**.

## Expanded benchmark

The V4 Milestone 2 benchmark contains nine cases:

| ID | Case | Result | Iterations | Final motion samples |
|---|---|---:|---:|---:|
| 01 | Cube | PASS | 1 | 0 |
| 02 | Pepper tag | PASS | 1 | 0 |
| 03 | Frog in teacup | PASS | 2 | 0 |
| 04 | Bishop | PASS | 1 | 0 |
| 05 | F-16 | PASS | 2 | 0 |
| 06 | Revolute hinge | PASS | 2 | 3 |
| 07 | Prismatic slider | PASS | 2 | 3 |
| 08 | Motion-collision repair | PASS | 2 | 3 |
| 09 | Two-joint serial arm | PASS | 2 | 9 |

Result: **9/9 PASS** with real OpenSCAD compilation/rendering and deterministic mesh validation.

## Artifacts added

- `motion_validator.py`
- expanded `kinematics.py`
- `tests/test_v4_motion.py`
- `benchmarks/prompts_v4_m2.json`
- `run_v4_m2_benchmarks.py`
- `corpus/patterns/mechanical_serial_chain.md`
- `runs/v4_milestone2_benchmark/benchmark_summary_v4_m2.json`

The planner/generator prompts and repair routing were also updated with the new kinematic conventions.

## Current limitations

1. Sampling proves only the sampled configurations, not continuous collision-free motion between samples.
2. Clearance distance is an approximate surface-distance diagnostic; exact interference uses OpenSCAD.
3. Kinematics currently assumes a tree-like parent-child mechanism. Closed-loop constraints such as a true four-bar linkage are not solved yet.
4. Dynamics, loads, strength, torque, friction, and bearing/contact analysis are outside the current scope.
5. Part-to-component mapping still uses declared origins and component centroids rather than explicit per-part source exports.
6. Live-model qualification remains pending because this sandbox has no OpenAI API key.

## Recommended Milestone 3

The next mechanical milestone should focus on continuous/adaptive collision sampling, explicit per-part generation/export contracts, and a constrained closed-loop mechanism such as a four-bar or crank-slider. That would force the IR to represent dependent joint relationships instead of treating every moving joint as an independent DOF.
