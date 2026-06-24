# `task_geometry__survey_traverse__bearing_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `survey_traverse`
3. Supported `query_id`s: `bearing_from_back_bearing`, `closed_traverse_missing_bearing`
4. Answer schema: `integer`
5. Annotation schema: `point_map`

## Program Contract
- `survey_bearing_angle_value(visible_station_line, visible_north_reference, known_bearing, branch=bearing_from_back_bearing|closed_traverse_missing_bearing) -> marked_bearing_degrees; scene=survey_traverse; scope=bearing_angle_value`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `survey_traverse`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point witnesses. Map annotation binds station and bearing roles:

- `station_a`
- `station_b`
- `reference_north`
- `target_direction`
- `turn_vertex` for traverse-turn queries

Numeric bearing labels, turn labels, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/survey_traverse.yaml`
- Task module: `trace/tasks/geometry/survey_traverse/bearing_angle_value.py`
