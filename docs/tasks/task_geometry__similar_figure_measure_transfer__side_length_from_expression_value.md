# `task_geometry__similar_figure_measure_transfer__side_length_from_expression_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `similar_figure_measure_transfer`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `similar_triangles_target_side_from_expression` or `similar_polygons_target_side_from_expression`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_similar_figure_marked_side_equation, unknown_role=target_side_length, formula_schema=similar_side_ratio_with_expression); scene=similar_figure_measure_transfer; scope=side_length_from_expression_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the queried side, its corresponding side, and the supporting side-ratio pair:

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
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/geo3k_marked_equations.py`
