# `task_geometry__pythagorean_tree__missing_square_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `pythagorean_tree`
5. Query ids: `hypotenuse_square_area`, `leg_square_area`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(attached_square_areas_on_right_triangle, unknown_role=square_area, formula_schema=pythagorean_square_area_sum); scene=pythagorean_tree; scope=missing_square_area_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `pythagorean_tree`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed bounding boxes for the full square regions needed by the active query. For `hypotenuse_square_area`, required keys are `unknown_hypotenuse_square`, `known_leg_square_1`, and `known_leg_square_2`. For `leg_square_area`, required keys are `unknown_leg_square`, `known_leg_square`, and `known_hypotenuse_square`. The public annotation does not duplicate one square under multiple keys; the private trace keeps the concrete geometric role, such as `leg_square_1` or `leg_square_2`, for verifier/debug metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/pythagorean_tree.yaml`
- Task module: `trace/tasks/geometry/pythagorean_tree/missing_square_area_value.py`
