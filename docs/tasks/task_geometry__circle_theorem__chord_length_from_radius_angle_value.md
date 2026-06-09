# `task_geometry__circle_theorem__chord_length_from_radius_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `chord_length_from_radius_and_central_angle`, `chord_length_from_radius_and_inscribed_angle`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_circle_radius_and_angle, unknown_role=chord_length, formula_schema=chord_length_from_radius_angle); scene=circle_theorem; scope=chord_length_from_radius_angle_value`

## Prompt Bundle
- Prompt text is loaded from the geometry circle prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses role-keyed pixel points for the circle center and chord endpoints; the inscribed-angle query also includes the inscribed angle vertex. Radius labels, angle labels, and the `?` chord cue are visible annotations plus verifier metadata, not separate annotation objects.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/chord_length.py`
