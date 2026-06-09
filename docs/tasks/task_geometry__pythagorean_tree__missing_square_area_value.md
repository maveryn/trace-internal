# `task_geometry__pythagorean_tree__missing_square_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `pythagorean_tree`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `hypotenuse_square_area`, `leg_square_area`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(attached_square_areas_on_right_triangle, unknown_role=square_area, formula_schema=pythagorean_square_area_sum); scene=pythagorean_tree; scope=missing_square_area_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed bounding boxes for the full square regions. Required keys are `target_square`, `hypotenuse_square`, `leg_square_1`, and `leg_square_2`. The target key may duplicate one of the role-specific square boxes because the annotation contract checks both the queried target binding and the geometric role binding.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/pythagorean_tree.py`
