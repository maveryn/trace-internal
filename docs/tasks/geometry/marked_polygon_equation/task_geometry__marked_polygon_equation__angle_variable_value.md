# `task_geometry__marked_polygon_equation__angle_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
3. Supported `query_id`: `single`
4. Answer schema: `number`
5. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_equal_angle_marked_polygon_equation, unknown_role=variable_value, formula_schema=equal_angle_expression_variable); scene=marked_polygon_equation; scope=angle_variable_value`

## Internal Construction Families
The public task has no semantic query branch. The sampled construction family is recorded as trace metadata:

- `marked_equal_angles_variable`
- `isosceles_triangle_base_angle_variable`
- `equilateral_median_right_angle_variable`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by the visible construction labels in the rendered diagram, usually `A`, `B`, and `C`, with `D` included when the construction has a median or right-angle foot. Each value is that labeled point's pixel coordinate.

Expression labels, angle arcs, tick marks, right-angle marks, distractor readouts, and solved variable values remain visible scene marks plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/angle_variable_value.py`
