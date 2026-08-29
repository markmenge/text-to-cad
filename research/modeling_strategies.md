# CAD Modeling Strategy Catalog

| Strategy | Use when | OpenSCAD pattern | Examples |
| --- | --- | --- | --- |
| Primitive CSG | Mostly boxes/cylinders/spheres | union/difference/intersection | cube, spacer, bracket |
| 2D extrusion | Constant cross-section | linear_extrude + polygon/text | tag, panel, sign |
| Revolve | Axially symmetric | rotate_extrude | cup, knob, chess piece |
| Shell | Hollow with controlled wall | outer minus inner | cup, enclosure |
| Hull / loft | Smooth changing sections | hull over stations | fuselage, animal torso |
| Sweep approximation | Path-driven tube/beam | hull between sampled sections | bent tube |
| Array / pattern | Repeated features | for loops | vents, teeth, hole arrays |
| Formula/library | Known mathematical family | functions/modules/library | gears, threads |
| Mechanism skeleton | Joints and axes dominate | frames plus component modules | gearbox, linkage |
| Imported mesh | Surface is too complex for CSG | import | scans, complex organic assets |

Selection rule: use the simplest representation that preserves function, requested dimensions, and recognizable silhouette. Compound objects should combine strategies.
