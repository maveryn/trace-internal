# `task_geometry__triangle_relations__centroid_median_segment_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query variant: `default`
5. Query id: one of `centroid_vertex_segment_length` or `centroid_whole_median_length`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a segment length on a triangle median using the centroid 2:1 division theorem.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target median segment cue first, followed by the given median segment label and midpoint marks.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
