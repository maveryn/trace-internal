# `task_geometry__triangle_congruence_correspondence__corresponding_side_value`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_congruence_correspondence`
5. Query id: `tick_mark_side_transfer`, `congruence_statement_side_transfer`, or `overlapping_triangle_side_transfer`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_congruent_triangle_corresponding_sides, unknown_role=target_side_length, formula_schema=cpctc_side_equality); scene=triangle_congruence_correspondence; scope=corresponding_side_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_triangle_congruence_correspondence_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the target side and the corresponding source side:

- `target_side_start`
- `target_side_end`
- `source_corresponding_side_start`
- `source_corresponding_side_end`

Tick marks, labels, congruence statements, and numeric side labels remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_congruence_correspondence.yaml`
- Task module: `trace/tasks/geometry/triangle_congruence_correspondence/corresponding_side_value.py`
