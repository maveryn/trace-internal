# `task_geometry__special_quadrilateral__algebraic_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `special_quadrilateral`
5. Query id: `parallelogram_opposite_angle_expression`, `parallelogram_consecutive_angle_expression`, `rhombus_diagonal_half_angle_expression`, or `kite_opposite_angle_expression`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_special_quadrilateral_algebraic_angle_relation, unknown_role=target_angle_value, formula_schema=special_quadrilateral_angle_equation); scene=special_quadrilateral; scope=algebraic_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_special_quadrilateral_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target and support angle vertices:

- `target_angle_vertex`
- `support_angle_vertex`
- diagonal endpoints when the active query uses a diagonal angle bisector

Expression labels, solved `x`, and theorem names remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/special_quadrilateral.yaml`
- Task module: `trace/tasks/geometry/special_quadrilateral/algebraic_angle_value.py`
