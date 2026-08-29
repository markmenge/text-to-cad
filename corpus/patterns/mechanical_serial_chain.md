# Mechanical Pattern: Serial Joint Chain

Use an explicit parent-child joint tree for serial mechanisms. The generated scene is the zero-value nominal pose. Each child part is a separate manifold solid. A downstream part inherits every ancestor transform before its own joint transform is applied.

For revolute joints, model a physical axis feature such as a shaft and clearance bore, and ensure the declared joint origin coincides with the modeled axis. For stacked planar links, separating link bodies in Z while placing parent shafts through child clearance bores provides a simple printable demonstrator.

Validate the Cartesian combinations of sampled joint values, not just each joint in isolation, because collisions can arise only when multiple joints move together.
