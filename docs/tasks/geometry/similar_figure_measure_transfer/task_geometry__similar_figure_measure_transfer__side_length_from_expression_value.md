# `task_geometry__similar_figure_measure_transfer__side_length_from_expression_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `single`
6. Answer schema: `number`
7. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_similar_figure_marked_side_equation, unknown_role=target_side_length, formula_schema=similar_side_ratio_with_expression); scene=similar_figure_measure_transfer; scope=side_length_from_expression_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Query and Construction Axes
- `single` is the only public query id.
- `construction_family` is replay metadata and may be `triangle_target_expression` or `polygon_target_expression`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by visible point labels for the queried side, its corresponding side, and the supporting side-ratio pair.

Expression labels, tick marks, vertex labels, and solved variable values remain visible scene content plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/side_length_from_expression_value.py`
