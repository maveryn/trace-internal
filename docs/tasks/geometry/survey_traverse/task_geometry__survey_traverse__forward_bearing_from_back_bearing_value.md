# `task_geometry__survey_traverse__forward_bearing_from_back_bearing_value`

## Contract
1. Domain: `geometry`
2. Scene id: `survey_traverse`
3. Task id: `task_geometry__survey_traverse__forward_bearing_from_back_bearing_value`
4. Supported `query_id`: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_map`

## Program Contract
- `survey_forward_bearing_from_back_bearing(visible_station_line, visible_north_reference, known_back_bearing) -> forward_bearing_degrees; scene=survey_traverse; scope=forward_bearing_from_back_bearing_value`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `survey_traverse`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point witnesses. Map annotation binds station and bearing roles:

- `station_a`
- `station_b`
- `reference_north`
- `target_direction`

Numeric bearing labels, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/survey_traverse.yaml`
- Task module: `trace/tasks/geometry/survey_traverse/forward_bearing_from_back_bearing_value.py`
