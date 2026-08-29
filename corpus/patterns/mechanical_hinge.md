# Mechanical Pattern: Revolute Hinge

Use when one rigid part rotates relative to another about one axis.

- Parts: grounded body, moving body; optionally a separate pin if physically modeled.
- Joint: revolute.
- Axis: unit vector along the hinge pin.
- Limits: explicit angular range in degrees.
- FDM: leave radial/axial clearance between moving surfaces. For ordinary FDM smoke tests, 0.3-0.5 mm is a useful starting range.
- Keep moving bodies as distinct solids. Do not use a Boolean union across the joint.
- Validate the declared number of physical parts and one intended DOF.
