# `task_geometry__graph_paper__triangle_type_count`

## Contract
1. Domain: `geometry`
2. Task group: `counting`
3. Scene id: `graph_paper`
4. Public query variant: `default`
5. Query id: `triangle_type_count`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_counting_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Count triangles matching the requested triangle class.

The public task uses the shared geometry `counting` implementation. The concrete query branch is recorded in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/counting.yaml`
- Task module: `trace/tasks/geometry/counting/value.py`
