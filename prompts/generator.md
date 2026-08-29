# Generator Stage

Generate or repair OpenSCAD using the common context, user request, engineering IR, mechanical IR, iteration, and feedback.

Return OpenSCAD source only: no Markdown fences or explanation.

For ordinary parts, preserve the proven single-body rules.

For a mechanical assembly:
- Represent every mechanical_ir part as a distinct closed solid in one OpenSCAD scene.
- Do NOT union moving parts together.
- Keep the number of disconnected closed solids equal to the number of declared physical parts.
- Place each part centroid reasonably near its declared origin_mm so the exporter can map mesh components back to part IDs.
- Include visible geometry that makes the intended revolute/prismatic relationship understandable.
- Respect moving-part clearance; touching or intersecting moving parts are failures.
- Make the modeled joint axis physically coincide with mechanical_ir origin_mm/axis.
- Treat the generated geometry as the zero-value nominal joint pose.
- In serial chains, downstream geometry must be positioned so inherited parent motion and its own joint motion are both physically valid.
- Keep parts individually manifold and printable.
- Use named modules for each part.
- On repair iterations preserve parts/joints that already validate and address the specific failure codes.

Favor robust parametric geometry over decorative complexity.
