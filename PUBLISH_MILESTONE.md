# Publish Milestone

## Status

The project is ready for a first private GitHub release. The current development line is the V4 Milestone 3 foundation on top of the V4.1.0-dev2 pipeline.

## Release checklist

- [x] Source, prompts, fixtures, benchmarks, tests, and engineering reports are versioned.
- [x] Python dependencies are declared in `requirements.txt`.
- [x] README documents prerequisites, offline execution, live execution, examples, and limitations.
- [x] A live-generated king example is included as a visual reference.
- [x] Offline regression suite passes with real OpenSCAD.
- [x] Generated runs, Python caches, local environments, and secrets are ignored.
- [x] Add a recorded live cassette for a representative prompt without committing credentials.
- [ ] Add a release tag after the first clean clone/install/test on another machine.
- [ ] Add slicer-backed wall/support/material validation before claiming print-ready output.

## Verified baseline

- Offline regression suite: 31/31 passing.
- V4 Milestone 2 benchmark: 9/9 passing.
- Four-bar demonstrator: explicit named part exports, one effective driver DOF, three sampled driver configurations, zero sampled collisions.
- Live king example: one iteration, score 96, watertight one-component STL, measured envelope `22 x 22 x 47.495 mm`.

## Release boundary

This is a reproducible research pipeline with live generation support. It is not yet a general-purpose CAD agent, a continuous motion solver, a slicer, or a mechanical strength/dynamics analysis system. Release notes should preserve that distinction.