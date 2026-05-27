# `task_geometry__triangle_relations__angle_bisector_segment_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query id: `default`
5. Query id: one of `angle_bisector_split_length` or `angle_bisector_base_length`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a triangle segment length using the angle bisector theorem.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target segment cue first, followed by supporting side-length labels, split-segment labels, and angle-bisector marks.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
