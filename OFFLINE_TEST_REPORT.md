# Offline LLM Pipeline Test Report

## Environment

- OpenSCAD executable: `/usr/bin/openscad`
- OpenSCAD version: 2021.01
- LLM mode: `mock`
- Fixture database: `mocks/mock_openai.json`

## Architecture under test

```text
User prompt
  -> LLMPlanner
  -> LLMGenerator
  -> OpenSCADCompiler
  -> DeterministicValidator (trimesh + render checks)
  -> LLMCritic
  -> CADController repair loop
```

`MockOpenAIClient` and `OpenAIClient` implement the same `LLMClient` interface. The controller does not know which implementation it is using.

## Automated tests

Eight offline tests pass:

1. Planner selects bishop strategy from prompt context.
2. F-16 iteration 1 selects the deliberately bad fixture.
3. F-16 iteration 2 selects the repair fixture only after connected-component feedback.
4. Frog repair fixture is selected only after thin-wall semantic feedback.
5. Cube completes successfully in one iteration.
6. F-16 is repaired using real `trimesh` connected-component feedback.
7. Frog/teacup is repaired using mock semantic-critic feedback.
8. OpenSCAD syntax failure is repaired from compiler feedback, while a permanent failure stops at the configured retry limit.

Unit/integration command:

```text
python -m unittest discover -s tests -v
```

Result: `8 tests, OK`.

## Five benchmark prompts

All five benchmark models have been exercised with the offline LLM path and real OpenSCAD execution. The combined serial benchmark command exceeded the execution-call timeout, so the remaining models were run independently.

- Cube: PASS.
- Pepper name tag: PASS, bounding box exactly 60 x 20 x 2 mm.
- Frog in teacup: PASS after semantic repair.
- Bishop: PASS, watertight, one component.
- F-16: PASS after connected-component repair.

## What this proves

The offline suite can prove software behavior around the LLM boundary: context propagation, state transitions, retry policy, compile/render invocation, deterministic validation, feedback routing, artifact promotion, and report generation.

## What this does not prove

The fixture mock does not prove novel LLM reasoning, visual understanding, CAD quality on unseen prompts, or repair creativity. Those require periodic real-model evaluation.

## Recommended next layer: record/replay

When API access is available, save normalized real OpenAI requests and responses as regression cassettes. Future offline runs can replay those exact responses through the current compiler/validator/controller. This gives three test levels:

1. Synthetic fixtures: deliberately exercise every branch.
2. Recorded real responses: prevent regressions against previously observed model behavior.
3. Live OpenAI evaluation: measure current model quality on the benchmark set.

## Prompt-stage refactor regression - 2026-08-23

Added versioned prompt assets:
- prompts/text-to-cad.md - common CAD policy/context
- prompts/planner.md - planner output contract
- prompts/generator.md - OpenSCAD generation/repair contract
- prompts/critic.md - semantic critic contract

Both MockOpenAIClient and OpenAIClient now use PromptLibrary. The mock assembles the same common + stage + runtime request structure used by live mode, while fixture matching remains deterministic.

Regression results:
- Prompt assembly tests: PASS (common prompt included; correct role-specific prompt selected).
- Existing contextual mock selection tests: PASS.
- Cube end-to-end real OpenSCAD test: PASS.
- F-16 validator-feedback repair test: PASS.
- Frog semantic-critic repair test: PASS.
- Compile-error repair test: PASS.
- Retry-exhaustion test: PASS.

The full suite exceeded one 45-second execution-call budget while rendering the frog case, so that case was rerun independently and passed in 21.4 seconds. The remaining end-to-end/fault tests passed together in 9.5 seconds. No regression failure remains.
