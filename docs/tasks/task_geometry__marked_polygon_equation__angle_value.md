# `task_geometry__marked_polygon_equation__angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `marked_polygon_equation`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `marked_equal_angle_from_expression` or `isosceles_triangle_angle_from_expression`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_equal_angle_marked_polygon_equation, unknown_role=target_angle_measure, formula_schema=equal_angle_expression); scene=marked_polygon_equation; scope=angle_value`

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
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/geo3k_marked_equations.py`
