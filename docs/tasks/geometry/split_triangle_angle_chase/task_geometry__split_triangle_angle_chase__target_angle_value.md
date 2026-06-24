# `task_geometry__split_triangle_angle_chase__target_angle_value`

## Contract
- Domain: `geometry`
- Scene id: `split_triangle_angle_chase`
- Task id: `task_geometry__split_triangle_angle_chase__target_angle_value`
- Supported `query_id` values: `single_cevian_triangle_angle_sum`, `shared_vertex_split_angle_sum`, `two_step_adjacent_triangle_angle_sum`
- Answer schema: `integer`
- Annotation schema: `point_map`

## Program Contract
- `formula.solve_unknown(split_triangle_angle_sum, target=angle_measure, support=visible_angle_labels, construction=single_cevian_triangle|shared_vertex_split|two_step_adjacent_triangles); scene=split_triangle_angle_chase; scope=target_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_split_triangle_angle_chase_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the visible labeled vertices in the split-triangle construction:

- `A`
- `B`
- `C`
- `D`

The annotation stays as `point_map` because the task requires multiple role-bound construction points. It is not a scalar annotation candidate.

## Query Details
- `single_cevian_triangle_angle_sum`: use two visible angles in one small triangle to solve the marked target angle.
- `shared_vertex_split_angle_sum`: use a visible small-triangle angle and a visible target-side shared vertex angle to solve the marked target angle at the shared vertex.
- `two_step_adjacent_triangle_angle_sum`: solve one missing shared-side angle from the left triangle, use the straight-angle relationship, then solve the target angle in the adjacent triangle.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Answer and annotation are bound from the same rendered execution trace after final scene transform.

## Source
- Config: `configs/domains/geometry/split_triangle_angle_chase.yaml`
- Task module: `trace/tasks/geometry/split_triangle_angle_chase/target_angle_value.py`
- Prompt bundle: `prompts/geometry/split_triangle_angle_chase/geometry_split_triangle_angle_chase_v1.json`
