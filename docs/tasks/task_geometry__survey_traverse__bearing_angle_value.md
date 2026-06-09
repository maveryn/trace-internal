# `task_geometry__survey_traverse__bearing_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `survey_traverse`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `bearing_from_back_bearing` or `closed_traverse_missing_bearing`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_survey_station_bearings, unknown_role=marked_bearing, formula_schema=survey_bearing_angle); scene=survey_traverse; scope=bearing_angle_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation binds station and bearing roles:

- `station_a`
- `station_b`
- `reference_north`
- `target_direction`
- `turn_vertex` for traverse-turn queries

Numeric bearing labels, turn labels, station labels, and field-note text remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/survey_traverse.py`
