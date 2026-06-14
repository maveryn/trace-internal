# `task_geometry__marked_polygon_equation__side_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
5. Query id: `isosceles_triangle_equal_side_variable`, `equilateral_triangle_equal_side_variable`, or `marked_polygon_equal_side_variable`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_equal_side_marked_polygon_equation, unknown_role=variable_value, formula_schema=equal_side_expression); scene=marked_polygon_equation; scope=side_variable_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the two equal sides used in the equation:

- `target_side_start`
- `target_side_end`
- `equal_side_start`
- `equal_side_end`

Expression labels, tick marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/side_variable_value.py`
