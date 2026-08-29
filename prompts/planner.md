# Planner Stage

Plan the CAD before coding. Read the common context, user request, retrieved knowledge, and manufacturing profile. Do not write OpenSCAD.

Return strict JSON only. For ordinary single-part objects use:
{
  "object_type": "short_snake_case_name",
  "strategies": ["strategy"],
  "dimensions_mm": [x, y, z] or null,
  "requirements": [{"id":"R1","type":"...","text":"..."}]
}

For a mechanism or assembly, also include:
{
  "mechanical_system": {
    "parts": [
      {"id":"base","role":"grounded support","origin_mm":[0,0,0],"grounded":true,"printable":true}
    ],
    "joints": [
      {"id":"J1","type":"revolute|prismatic|fixed","parent":"base","child":"arm","axis":[0,0,1],"origin_mm":[0,0,0],"limits":[0,90],"clearance_mm":0.4}
    ],
    "expected_dof": 1,
    "assembly_notes": ["concise mechanical intent"]
  }
}

Rules:
- Use millimeters.
- Preserve explicit dimensional, semantic, manufacturing, and motion requirements.
- A mechanical part ID must be unique and stable.
- Exactly one part should be grounded for a simple mechanism.
- Use fixed joints for rigid relationships, revolute for rotation, and prismatic for sliding.
- Moving joint axes must be normalized.
- Specify meaningful motion limits and FDM clearance for moving joints.
- Joint origin_mm and axis are expressed in the parent part's nominal coordinate frame.
- The generated assembly is the joint-value-zero nominal pose; if zero is outside a joint's legal limits, use the nearest legal pose and state it in assembly_notes.
- For serial mechanisms, parent/child relationships must form a directed kinematic tree rooted at the grounded part.
- Mechanical-system dimensions_mm should be null unless the complete assembly envelope is explicitly constrained in all 3 axes.
