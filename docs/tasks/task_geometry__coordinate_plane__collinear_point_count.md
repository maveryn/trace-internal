# `task_geometry__coordinate_plane__collinear_point_count`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query variant: `default`
5. Query id: `collinear_count`
6. Answer type: `integer`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Count points collinear with the marked reference line.

The public task uses the shared geometry `coordinate` implementation. The concrete query branch is recorded in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Task module: `trace/tasks/geometry/coordinate/relation.py`
