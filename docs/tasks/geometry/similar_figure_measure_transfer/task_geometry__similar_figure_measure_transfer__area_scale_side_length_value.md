# `task_geometry__similar_figure_measure_transfer__area_scale_side_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `side_length_from_area_pair`, `side_length_from_area_ratio`, or `side_length_from_area_and_known_side`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_similar_figure_area_scale_relation, unknown_role=target_corresponding_side_length, formula_schema=area_scale_to_linear_scale); scene=similar_figure_measure_transfer; scope=area_scale_side_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_similar_figure_measure_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target side endpoints and the corresponding source side endpoints:

- `target_side_start`
- `target_side_end`
- `source_corresponding_side_start`
- `source_corresponding_side_end`

Area labels, area ratios, tick marks, and derived scale factors remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/area_scale_side_length_value.py`
