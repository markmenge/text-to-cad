# Text-to-CAD v3 Milestone 1 Report

## Status

Pipeline version: 3.0.0-dev1

Milestone 1 is implemented and regression-tested. V3 is not yet declared complete.

## Implemented

- Deterministic offline CAD knowledge retrieval over corpus/patterns and research Markdown.
- Domain query expansion for common CAD object families such as F-16/aircraft, bishops, teacups, and name tags.
- Relevance cutoff to avoid injecting weak unrelated context.
- Engineering intermediate representation containing object type, primary/secondary strategies, subsystems, symmetry, constraints, manufacturing process, and retrieved pattern provenance.
- Planner runtime context now includes retrieved patterns and a manufacturing profile.
- Generator runtime context now includes the engineering IR, retrieved patterns, manufacturing profile, failure codes, and repair route.
- Generic FDM manufacturing profile with build-volume/minimum-feature metadata.
- Honest slicer discovery: no external slicer is reported as available in this sandbox, and the pipeline does not pretend to perform slicing.
- Deterministic manufacturing-envelope validation.
- Knowledge capture from successful validated runs as JSON plus retrievable Markdown records.
- Successful knowledge is available to subsequent controller instances through the same offline retriever.
- V2 mock/replay/prompt/observability compatibility preserved.

## Regression result

Legacy + V3 feature unit/integration tests: 13/13 PASS.

Five benchmark prompts were exercised through the V3 path with real /usr/bin/openscad:

| Benchmark | Result | Iterations |
| --- | --- | ---: |
| Cube | PASS | 1 |
| Pepper name tag | PASS | 1 |
| Frog in teacup | PASS | 2 |
| Bishop | PASS | 1 |
| F-16 | PASS | 2 |

The F-16 continues to exercise connectivity repair. The frog continues to exercise manufacturing/semantic repair.

## Retrieval regression discovered and fixed

The first F-16 retrieval test ranked the broad historical research note above the dedicated aircraft pattern because the raw term F-16 did not lexically overlap with aircraft/fuselage/wing terminology. Deterministic domain expansion was added, and the dedicated aircraft pattern now ranks correctly. A relative-score cutoff was also added so weak context is not injected merely to fill the top-k list.

## Knowledge accumulation

Validated successful runs now create compact records under knowledge/successes. Each record contains the prompt, object type, chosen strategies, subsystems, final metrics, iteration count, provenance, and pipeline version. A Markdown companion makes the record retrievable offline.

## Manufacturing status

The sandbox contains OpenSCAD 2021.01 but no discovered PrusaSlicer, Cura, OrcaSlicer, or SuperSlicer executable. V3 therefore currently performs honest manufacturing-envelope checks only. Real slicer integration remains a V3 completion item.

## Remaining V3 work

- Add a real external slicer backend and parse slicer output when an executable is available.
- Extend engineering IR to explicit assemblies, joints, degrees of freedom, clearances, and interfaces.
- Add at least one constrained mechanical assembly benchmark.
- Add failure-derived knowledge capture, not only successful-run capture.
- Add retrieval evaluation metrics and ablation testing: no retrieval vs static corpus vs accumulated knowledge.
- Run live-model benchmark studies to measure whether retrieval/IR improve first-pass and final success rates.
- Decide promotion criteria from 3.0.0-dev to a stable v3 release based on measured live improvement.
