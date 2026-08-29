# High-Level Goals

## Vision

Make text-to-CAD dependable enough that a person can describe a physical object in ordinary language and receive a validated, manufacturable model with confidence that the result matches the intent.

The project should aim beyond being an OpenSCAD code generator. It should become an open, testable engineering system for translating human intent into physical geometry.

## 1. Make AI-Generated CAD Dependable

Move text-to-CAD from "generate and hope" to an engineering discipline.

A generated model should be planned, built, rendered, measured, criticized, repaired, and validated before it is considered complete. Failures should be detected by the system rather than discovered by the user after opening the model or attempting to manufacture it.

## 2. Establish an Open Benchmark for Text-to-CAD

Create a respected, reproducible benchmark that measures increasingly difficult CAD tasks across dimensions such as:

- dimensional accuracy
- geometric validity
- semantic fidelity
- manufacturability
- constraint satisfaction
- repair ability
- complexity
- reliability across repeated runs

The benchmark should make it possible to compare models, prompting strategies, CAD representations, and agent architectures objectively.

## 3. Build a Model-Independent CAD Agent Architecture

The intelligence layer should be replaceable.

The project should support different LLMs, local models, future reasoning systems, and deterministic components without redesigning the CAD pipeline. Improvements in foundation models should automatically make the system more capable rather than make the architecture obsolete.

## 4. Create a General Intermediate Representation for Physical Intent

Natural language should not map directly to arbitrary CAD source whenever a better representation is possible.

Develop a structured representation that captures:

- objects and subsystems
- dimensions
- features
- symmetry
- relationships
- constraints
- joints
- motion
- manufacturing requirements
- modeling strategies

This representation should become a bridge between human intent, AI reasoning, CAD languages, geometry kernels, and manufacturing tools.

## 5. Make Validation a First-Class Part of Generative CAD

A model is not complete because CAD software successfully compiled it.

Validation should combine deterministic geometry analysis, dimensional checks, multiple rendered views, semantic inspection, manufacturing rules, and eventually slicing or simulation.

Every important requirement from the original request should be traceable to evidence showing whether it passed, failed, or remains uncertain.

## 6. Make Failure Useful

Every failed generation should produce information that improves the system.

Failures should be reproducible, classified, logged, and suitable for automated analysis. Over time, the project should build a corpus of real text-to-CAD failure modes and successful repairs.

The system should increasingly know not only how to generate geometry, but how CAD generation fails and how to recover.

## 7. Learn from Successful Designs and Repairs

Build a reusable knowledge base of modeling patterns, successful constructions, validation techniques, and repair strategies.

The system should retrieve relevant prior knowledge when solving new problems rather than repeatedly rediscovering the same geometric techniques.

This knowledge should remain inspectable and useful independently of any particular LLM.

## 8. Progress from Shapes to Mechanical Systems

The long-term target should extend beyond static decorative models.

Support assemblies containing parts and physical relationships such as:

- fixed connections
- hinges
- sliders
- shafts
- bearings
- gears
- springs
- cables
- clearances
- fasteners
- motion limits

A user should eventually be able to describe what a mechanism must do, not merely what it should look like.

## 9. Connect Language Directly to Manufacturing

Close the loop from description to a physical result.

The eventual pipeline should be capable of progressing through:

Human intent -> engineering plan -> parametric CAD -> validation -> manufacturing preparation -> fabrication

For FDM printing, this means eventually validating orientation, wall thickness, tolerances, supports, slicing, material assumptions, and printer constraints before declaring a model ready.

## 10. Make Results Reproducible and Auditable

Every generated artifact should have provenance.

A run should record enough information to reproduce and understand the result, including prompts, planning decisions, model versions, source code, tool versions, validation evidence, repairs, and final artifacts.

Text-to-CAD should be testable like software rather than treated as an opaque AI interaction.

## 11. Become a Platform for CAD-Agent Research

Make the repository useful to researchers, engineers, model developers, and hobbyists who want to experiment with generative engineering.

It should be easy to:

- add a new LLM
- add a new CAD backend
- add a validator
- add benchmark problems
- compare strategies
- replay historical model behavior
- study failures
- contribute modeling knowledge

The repository should become infrastructure on which other text-to-CAD work can be built.

## 12. Demonstrate That AI Can Engineer, Not Merely Draw

The ultimate goal is to demonstrate a meaningful transition from generative appearance to generative engineering.

Success means the system can take an underspecified human idea, reason about its physical structure, create an appropriate parametric representation, test its own work, identify failures, repair them, and produce an artifact that can exist in the physical world.

If achieved broadly and reliably, that capability would represent something substantially more important than automatic CAD generation: a practical interface between human intent, machine reasoning, and manufacturing.
