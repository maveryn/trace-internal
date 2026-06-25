# `task_geometry__survey_traverse__station_elevation_value`

## Contract
1. Domain: `geometry`
2. Scene id: `survey_traverse`
3. Task id: `task_geometry__survey_traverse__station_elevation_value`
4. Supported `query_id`s: `leveling_station_elevation`, `slope_distance_elevation_change`
5. Answer schema: `integer`
6. Annotation schema: `point_map`

## Program Contract
- `survey_station_elevation_value(visible_station_profile, visible_field_note, branch=leveling_station_elevation|slope_distance_elevation_change) -> target_station_elevation; scene=survey_traverse; scope=station_elevation_value`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `survey_traverse`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point witnesses. Map annotation binds station and measurement roles:

- `reference_station`
- `target_station`
- `measurement_line`
- `field_note_region`

Numeric elevations, staff readings, slope rates, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/survey_traverse.yaml`
- Task module: `trace/tasks/geometry/survey_traverse/station_elevation_value.py`
