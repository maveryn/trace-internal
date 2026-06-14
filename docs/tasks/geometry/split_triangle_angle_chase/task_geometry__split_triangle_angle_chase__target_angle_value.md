# `task_geometry__split_triangle_angle_chase__target_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `split_triangle_angle_chase`
5. Query id: `single_cevian_triangle_angle_sum`, `shared_vertex_split_angle_sum`, or `two_step_adjacent_triangle_angle_sum`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(split_triangle_angle_sum, unknown_role=target_angle, formula_schema=triangle_angle_sum_or_straight_angle_chain); scene=split_triangle_angle_chase; scope=target_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_split_triangle_patterns_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target angle and the visible supporting angle witnesses:

- `target_angle`
- `given_angle_1`
- `given_angle_2`
- optional `given_angle_3`
- optional `shared_straight_angle_vertex`

Angle labels, vertex labels, shaded subtriangles, and split-segment linework remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/split_triangle_angle_chase.yaml`
- Task module: `trace/tasks/geometry/split_triangle_angle_chase/target_angle_value.py`
