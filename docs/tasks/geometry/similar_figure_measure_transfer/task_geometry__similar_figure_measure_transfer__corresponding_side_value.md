# `task_geometry__similar_figure_measure_transfer__corresponding_side_value`

## Contract
1. Domain: `geometry`
2. Scene id: `similar_figure_measure_transfer`
5. Query id: `direct_side_transfer`, `two_pair_side_transfer`, or `nested_side_transfer`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_similar_figure_side_relation, unknown_role=target_corresponding_side_length, formula_schema=linear_scale_transfer); scene=similar_figure_measure_transfer; scope=corresponding_side_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_similar_figure_measure_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the target side and the corresponding source/support sides:

- `target_side_start`
- `target_side_end`
- `source_corresponding_side_start`
- `source_corresponding_side_end`
- optional support-side endpoint keys when a second side pair is shown

Side labels, tick marks, figure labels, scale factors, and derived values remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similar_figure_measure_transfer.yaml`
- Task module: `trace/tasks/geometry/similar_figure_measure_transfer/corresponding_side_value.py`
