# `task_geometry__similar_figure_measure_transfer__scale_factor_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `scale_factor_from_side_pair`, `scale_factor_from_perimeter_pair`, or `scale_factor_from_area_pair`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_similar_figure_measure_pair, unknown_role=linear_scale_factor, formula_schema=side_perimeter_or_area_scale); scene=similar_figure_measure_transfer; scope=scale_factor_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_similar_figure_measure_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the two figure anchors and, when side measurements are shown, the endpoints of the reference side pair:

- `source_figure_anchor`
- `target_figure_anchor`
- `source_reference_side_start`
- `source_reference_side_end`
- `target_reference_side_start`
- `target_reference_side_end`

Perimeter and area labels remain visible annotations plus verifier metadata, not public annotation boxes.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/scale_factor_value.py`
