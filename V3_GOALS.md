# Text-to-CAD v3 Goals

V3 moves the project from a reproducible closed-loop generator toward a system that accumulates and applies engineering knowledge.

## V3.1 Knowledge-aware generation
- Retrieve relevant modeling patterns before planning.
- Keep retrieval deterministic and offline-capable.
- Inject the same retrieved context into mock, replay, and live modes.

## V3.2 Engineering intermediate representation
- Represent primary/secondary strategies, subsystems, symmetry, constraints, and manufacturing process explicitly.
- Treat the IR as the contract between planning and generation.
- Keep backward compatibility with older planner responses while fixtures migrate.

## V3.3 Manufacturing-aware validation
- Introduce an explicit FDM manufacturing profile.
- Validate machine build envelope and other deterministic constraints that can be measured honestly.
- Discover external slicers when present; never pretend slicing was performed when no slicer exists.

## V3.4 Learning from successful runs
- Capture compact reusable records from validated successful generations.
- Make accumulated successes available as future retrieval material.
- Preserve provenance so learned patterns can be traced to the run and pipeline version that produced them.

## V3.5 Broader engineering capability
- Expand the IR toward assemblies, joints, degrees of freedom, clearances, and mechanical relationships.
- Add mechanical benchmark cases after static-part regressions remain stable.

## V3 completion direction
V3 is complete when knowledge retrieval and engineering IR measurably improve live benchmark performance, successful-run knowledge can be replayed/retrieved safely, manufacturing validation includes a real slicer backend on supported systems, and at least one constrained mechanical assembly benchmark runs end-to-end.
