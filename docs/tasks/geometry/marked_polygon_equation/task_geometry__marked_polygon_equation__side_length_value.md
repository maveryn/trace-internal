# `task_geometry__marked_polygon_equation__side_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `marked_polygon_equation`
3. Supported `query_id`: `single`
4. Answer schema: `number`
5. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_equal_side_marked_polygon_equation, unknown_role=target_side_length, formula_schema=equal_side_expression_length); scene=marked_polygon_equation; scope=side_length_value`

## Internal Construction Families
The public task has no semantic query branch. The sampled construction family is recorded as trace metadata:

- `isosceles_triangle_side_from_expression`
- `equilateral_triangle_side_from_expression`
- `marked_polygon_side_from_expression`
- `equilateral_median_side_length_from_expression`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by the visible construction labels in the rendered diagram, usually `A`, `B`, and `C`, with `D` included when the construction has a median. Each value is that labeled point's pixel coordinate.

Expression labels, tick marks, target side labels, and distractor readouts remain visible scene marks plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/marked_polygon_equation.yaml`
- Task module: `trace/tasks/geometry/marked_polygon_equation/side_length_value.py`
