# Critic Stage

Judge semantic correctness, printability, and mechanical plausibility using the request, IRs, deterministic results, metrics, source, and rendered views.

Return strict JSON only:
{
  "pass": true or false,
  "score": 0,
  "feedback": ["specific repair instruction"],
  "requirement_results": []
}

For mechanisms also verify that the render plausibly shows the declared parts and joint relationship. Do not override deterministic joint-graph, part-count, clearance, or DOF failures. Feedback should name the smallest useful mechanical or geometric repair.
