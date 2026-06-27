# `task_geometry__marked_polygon_equation__polygon_angle_sum_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
3. Supported `query_id`: `single`
4. Answer schema: `number`
5. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_polygon_interior_angle_sum_equation, unknown_role=variable_value, formula_schema=polygon_angle_sum_variable); scene=marked_polygon_equation; scope=polygon_angle_sum_variable_value`

## Internal Construction Families
The public task has no semantic query branch. The sampled construction family is recorded as trace metadata:

- `triangle_angle_sum_variable`
- `quadrilateral_angle_sum_variable`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by the visible polygon vertex labels, usually `A`, `B`, and `C` for triangles or `A`, `B`, `C`, and `D` for quadrilaterals. Each value is that labeled point's pixel coordinate.

Angle expressions, numeric angle readouts, side distractors, and solved variable values remain visible scene marks plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/polygon_angle_sum_variable_value.py`
