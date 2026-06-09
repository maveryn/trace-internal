# `task_geometry__triangle_relations__angle_bisector_variable_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `split_segment_ratio_variable` or `adjacent_side_ratio_variable`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(angle_bisector_theorem_variable, unknown_role=variable_value, formula_schema=angle_bisector_side_split_ratio); scene=triangle_relations; scope=angle_bisector_variable_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_split_triangle_patterns_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the angle-bisector vertex, split point, and role-bound side or split-segment endpoints:

- `angle_vertex`
- `split_point`
- `left_side_start`
- `left_side_end`
- `right_side_start`
- `right_side_end`
- `left_split_start`
- `left_split_end`
- `right_split_start`
- `right_split_end`

Expression labels, tick marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/split_triangle_patterns.py`
