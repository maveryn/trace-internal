# `task_geometry__marked_polygon_equation__side_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `marked_polygon_equation`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `isosceles_triangle_side_from_expression`, `equilateral_triangle_side_from_expression`, or `marked_polygon_side_from_expression`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_equal_side_marked_polygon_equation, unknown_role=target_side_length, formula_schema=equal_side_expression); scene=marked_polygon_equation; scope=side_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the queried side and equal supporting side:

- `target_side_start`
- `target_side_end`
- `equal_side_start`
- `equal_side_end`

Expression labels, tick marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/geo3k_marked_equations.py`
