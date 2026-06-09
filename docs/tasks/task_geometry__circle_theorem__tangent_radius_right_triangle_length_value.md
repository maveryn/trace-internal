# `task_geometry__circle_theorem__tangent_radius_right_triangle_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `radius_from_external_distance_and_angle`, `tangent_length_from_radius_and_external_distance`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_tangent_radius_right_triangle, unknown_role=length_measure, formula_schema=tangent_radius_right_triangle); scene=circle_theorem; scope=tangent_radius_right_triangle_length_value`

## Prompt Bundle
- Prompt text is loaded from the geometry circle prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses role-keyed pixel points for the circle center, tangent point, and exterior point. Length labels, angle labels, target cues, and the right-angle marker are visible annotations plus verifier metadata, not separate public annotation objects.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/tangent_radius.py`
