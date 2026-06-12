# `task_geometry__marked_polygon_equation__angle_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
3. Scene id: `marked_polygon_equation`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `marked_equal_angles_variable` or `isosceles_triangle_base_angle_variable`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_equal_angle_marked_polygon_equation, unknown_role=variable_value, formula_schema=equal_angle_expression); scene=marked_polygon_equation; scope=angle_variable_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the queried angle and the equal supporting angle:

- `target_angle_vertex`
- `target_angle_ray_1`
- `target_angle_ray_2`
- `equal_angle_vertex`
- `equal_angle_ray_1`
- `equal_angle_ray_2`

Expression labels, angle arcs, tick marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/angle_variable_value.py`
