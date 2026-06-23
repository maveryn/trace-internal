# `task_geometry__marked_polygon_equation__angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
3. Supported `query_id`: `single`
4. Answer schema: `number`
5. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_equal_angle_marked_polygon_equation, unknown_role=target_angle_measure, formula_schema=equal_angle_expression_measure); scene=marked_polygon_equation; scope=angle_value`

## Internal Construction Families
The public task has no semantic query branch. The sampled construction family is recorded as trace metadata:

- `marked_equal_angle_from_expression`
- `isosceles_triangle_angle_from_expression`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by the visible construction labels in the rendered diagram, usually `A`, `B`, `C`, and `D` for quadrilateral cases or `A`, `B`, and `C` for triangle cases. Each value is that labeled point's pixel coordinate.

Expression labels, angle arcs, equal-side tick marks, and target angle labels remain visible scene marks plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/angle_value.py`
