# Offline Mock OpenAI Design

The text-to-CAD pipeline treats the LLM as a replaceable interface. The same planner, generator, critic, controller, OpenSCAD compiler, and validators run in both modes:

```text
--llm mock     -> MockOpenAIClient -> mocks/mock_openai.json
--llm openai   -> OpenAIClient     -> OpenAI Responses API
```

## Why this is useful

The offline mock tests orchestration rather than model intelligence. It can verify:

- planner output is passed to generation;
- prompt and strategy context are preserved;
- OpenSCAD compile failures reach the repair iteration;
- geometric validator feedback reaches the generator;
- semantic critic feedback reaches the generator;
- retry limits work;
- the correct artifacts are promoted to final output;
- reports retain a complete iteration history;
- online and offline LLM clients share the same interface.

## Contextual fixture matching

Each JSON rule may match:

- LLM role: planner, generator, critic;
- words in the original user prompt;
- planned object type;
- modeling strategies;
- iteration number;
- words in prior feedback.

The highest-specificity matching fixture wins.

This makes the mock stateful enough to exercise closed-loop repair. For example:

1. F-16 iteration 1 returns wings disconnected from the fuselage.
2. `trimesh` detects multiple connected components.
3. The controller sends that feedback into iteration 2.
4. The mock selects `gen_f16_repair` only because the context contains `components`.
5. OpenSCAD recompiles the repaired model and the validator verifies one component.

The frog benchmark exercises a different route: its first mesh is geometrically valid, but the mock semantic critic rejects its deliberately thin wall. That critic feedback drives the repair.

## What mock testing cannot prove

Fixtures cannot measure actual LLM CAD intelligence, prompt adherence, visual recognition, or novel repair ability. Those become a separate online evaluation layer. Offline fixtures should therefore be used for deterministic software regression tests, while periodic real-model runs measure model quality.
