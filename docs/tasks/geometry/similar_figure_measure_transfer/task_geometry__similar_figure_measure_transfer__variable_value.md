# `task_geometry__similar_figure_measure_transfer__variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `similar_triangles_side_ratio_variable`, `similar_polygons_side_ratio_variable`, or `two_expression_side_ratio_variable`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_similar_figure_marked_side_equation, unknown_role=variable_value, formula_schema=similar_side_ratio); scene=similar_figure_measure_transfer; scope=variable_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the side pair containing the variable and the supporting corresponding side pair:

- `target_side_start`
- `target_side_end`
- `corresponding_side_start`
- `corresponding_side_end`
- `support_source_side_start`
- `support_source_side_end`
- `support_target_side_start`
- `support_target_side_end`

Expression labels, tick marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/variable_value.py`
