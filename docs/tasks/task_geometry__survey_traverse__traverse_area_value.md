# `task_geometry__survey_traverse__traverse_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `survey_traverse`
3. Scene id: `survey_traverse`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `coordinate_traverse_area` or `offset_trapezoid_area`
6. Answer schema: `integer`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_survey_traverse_field_notes, unknown_role=enclosed_area, formula_schema=survey_traverse_area); scene=survey_traverse; scope=traverse_area_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `survey_traverse`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation binds the visual area witnesses:

- `traverse_region`
- `field_note_region`
- `area_reference_region`

Coordinate values, chainages, offsets, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/survey_traverse.yaml`
- Task module: `trace/tasks/geometry/survey_traverse/traverse_area_value.py`
