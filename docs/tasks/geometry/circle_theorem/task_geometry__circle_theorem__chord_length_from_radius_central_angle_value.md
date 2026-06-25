# `task_geometry__circle_theorem__chord_length_from_radius_central_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_theorem`
4. Query id: `single`
5. Answer schema: `decimal_value_1dp`
6. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_circle_radius_and_central_angle, unknown_role=chord_length, formula_schema=chord_length_from_radius_central_angle); scene=circle_theorem; scope=chord_length_from_radius_central_angle_value`

## Prompt Bundle
- Prompt text is loaded from the geometry circle prompt bundle configured for this scene package/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for `O`, `A`, and `B`, where `O` is the circle center and `A`/`B` are the chord endpoints. Radius labels, angle labels, and the `?` chord cue are visible annotations plus verifier metadata, not separate annotation objects.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_theorem.yaml`
- Task module: `trace/tasks/geometry/circle_theorem/chord_length_from_radius_central_angle_value.py`
