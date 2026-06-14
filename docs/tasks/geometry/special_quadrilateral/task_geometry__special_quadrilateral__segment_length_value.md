# `task_geometry__special_quadrilateral__segment_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `special_quadrilateral`
5. Query id: `parallelogram_opposite_side_expression`, `rhombus_all_sides_expression`, `kite_adjacent_equal_side_expression`, or `parallelogram_diagonal_bisection_expression`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_special_quadrilateral_algebraic_segment_relation, unknown_role=target_segment_length, formula_schema=special_quadrilateral_segment_equation); scene=special_quadrilateral; scope=segment_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_special_quadrilateral_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the target and support segments:

- `target_segment_start`
- `target_segment_end`
- `support_segment_start`
- `support_segment_end`

Expression labels, solved `x`, and theorem names remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/special_quadrilateral.yaml`
- Task module: `trace/tasks/geometry/special_quadrilateral/segment_length_value.py`
