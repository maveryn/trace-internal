# `task_geometry__triangle_congruence_correspondence__algebraic_side_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_congruence_correspondence`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `single_expression_equal_sides`, `two_expression_equal_sides`, or `shared_side_congruence_expression`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_congruent_triangle_algebraic_side_correspondence, unknown_role=target_side_length, formula_schema=cpctc_algebraic_side_equality); scene=triangle_congruence_correspondence; scope=algebraic_side_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_triangle_congruence_correspondence_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target side, corresponding source side, and algebraic support side pair:

- `target_side_start`
- `target_side_end`
- `source_corresponding_side_start`
- `source_corresponding_side_end`
- `support_source_side_start`
- `support_source_side_end`
- `support_target_side_start`
- `support_target_side_end`

Algebraic labels, solved `x`, tick marks, labels, and congruence statements remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/triangle_congruence_correspondence.py`
