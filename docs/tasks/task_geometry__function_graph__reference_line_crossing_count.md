# `task_geometry__function_graph__reference_line_crossing_count`

## Contract
1. Domain: `geometry`
2. Task group: `graphing`
3. Scene id: `function_graph`
4. Public query variant: `default`
5. Query id: `reference_line_crossing_count`
6. Answer type: `integer`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_graphing_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Count intersections between the function graph and a reference line.

The public task uses the shared geometry `graphing` implementation. The concrete query branch is recorded in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/graphing.yaml`
- Task module: `trace/tasks/geometry/graphing/count.py`
