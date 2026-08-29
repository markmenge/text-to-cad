# Text-to-CAD Common Context

Mission: convert a human CAD request into dependable printable geometry. Optimize for a model that compiles, matches explicit dimensions, is structurally coherent, and survives deterministic and visual validation.

## Units and coordinates
- Use millimeters and +Z as up.
- Put the intended print base on or above Z=0.
- Treat explicit dimensions as requirements.
- Preserve natural symmetry.

## Plan before coding
Choose a representation before writing OpenSCAD:
- Primitive CSG: boxes, blocks, brackets, panels.
- 2D sketch + linear_extrude: tags, plates, signs, flat profiles.
- Profile + rotate_extrude: cups, knobs, chess pieces, axisymmetric bodies.
- hull/blended primitives: organic forms, aircraft bodies, smooth transitions.
- Formula/library generator: gears, threads, repeated engineered features.
- Mesh/import only when native parametric construction is unsuitable.
Prefer the simplest robust representation.

## Printability defaults
- Produce one connected printable object unless requested otherwise.
- Avoid zero-thickness surfaces and coincident-only contacts.
- Make joints overlap meaningfully.
- Use practical wall/base thicknesses.
- Keep the model watertight/manifold when possible.

## Repair policy
Validation and critique describe the previous iteration. Fix the smallest relevant part first and preserve geometry that already works. Repair compile errors before geometry. Multiple components require real intersection. Correct dimensional failures without gratuitous redesign. Semantic failures require recognizable feature improvement. Never repeat a failed design unchanged.

## OpenSCAD reliability
Prefer modules and named parameters for nontrivial models. Avoid fragile coplanar Boolean boundaries. Use difference() for holes/cavities and union()/hull() for connected construction. Extrude requested text into real geometry. Use deterministic geometry.

## Success
Success requires deterministic build/mesh checks and semantic agreement with the request.

## Mechanical Systems
When the request describes multiple parts that move or constrain one another, treat it as a mechanical system rather than forcing it into a single fused STL.
- Give each physical part a stable ID.
- Represent rigid and moving relationships explicitly as joints.
- Support fixed, revolute, and prismatic joints first; extend only with validation support.
- Declare one grounded reference part for simple mechanisms.
- Declare normalized joint axes, joint origins, motion limits, and moving clearances.
- Moving parts must remain separate printable solids; intentional rigid subfeatures within one part should be connected.
- Degrees of freedom are engineering requirements and must be validated.
- Prefer mechanisms whose geometry makes the intended motion understandable from multiple views.
