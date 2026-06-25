# `task_geometry__survey_traverse__traverse_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `survey_traverse`
3. Task id: `task_geometry__survey_traverse__traverse_area_value`
4. Supported `query_id`s: `coordinate_traverse_area`, `offset_trapezoid_area`
5. Answer schema: `integer`
6. Annotation schema: `bbox_map`

## Program Contract
- `survey_traverse_area_value(visible_traverse_shape, visible_field_note, branch=coordinate_traverse_area|offset_trapezoid_area) -> enclosed_area; scene=survey_traverse; scope=traverse_area_value`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `survey_traverse`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space box witnesses. Map annotation binds the visual area witnesses:

- `traverse_region`
- `field_note_region`
- `area_reference_region`

Coordinate values, chainages, offsets, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/survey_traverse.yaml`
- Task module: `trace/tasks/geometry/survey_traverse/traverse_area_value.py`
