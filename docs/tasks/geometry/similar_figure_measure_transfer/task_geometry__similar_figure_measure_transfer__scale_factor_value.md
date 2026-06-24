# `task_geometry__similar_figure_measure_transfer__scale_factor_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `scale_factor_from_side_pair`, `scale_factor_from_perimeter_pair`, or `scale_factor_from_area_pair`
6. Answer schema: `integer`
7. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_similar_figure_measure_pair, unknown_role=linear_scale_factor, formula_schema=side_perimeter_or_area_scale); scene=similar_figure_measure_transfer; scope=scale_factor_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_similar_figure_measure_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by visible point labels. For side-pair queries the keys mark the reference corresponding side endpoints. For perimeter and area queries the keys mark the comparable figures' vertices.

Perimeter and area labels remain visible scene content plus verifier metadata, not public annotation boxes.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/scale_factor_value.py`
