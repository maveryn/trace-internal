# `task_geometry__pythagorean_tree__missing_square_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `pythagorean_tree`
3. Task id: `task_geometry__pythagorean_tree__missing_square_area_value`
4. Query ids: `hypotenuse_square_area`, `leg_square_area`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; each query always asks for three role-bound square-region witnesses)

## Program Contract
- `solve_formula(attached_square_areas_on_right_triangle, unknown_role=square_area, formula_schema=pythagorean_square_area_sum); scene=pythagorean_tree; scope=missing_square_area_value`

## Query Semantics
- `hypotenuse_square_area` asks for the area of the square attached to the hypotenuse when both leg-square areas are visible.
- `leg_square_area` asks for one missing leg-square area when the hypotenuse-square area and the other leg-square area are visible.
- The concrete target leg, integer right-triangle triple, fill palette, font, layout, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/pythagorean_tree/geometry_pythagorean_tree_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed bounding boxes for the full square regions needed by the active query. For `hypotenuse_square_area`, required keys are `unknown_hypotenuse_square`, `known_leg_square_1`, and `known_leg_square_2`. For `leg_square_area`, required keys are `unknown_leg_square`, `known_leg_square`, and `known_hypotenuse_square`. The public annotation does not duplicate one square under multiple keys; the private trace keeps the concrete geometric role, such as `leg_square_1` or `leg_square_2`, for verifier/debug metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/pythagorean_tree.yaml`
- Prompt bundle: `prompts/geometry/pythagorean_tree/geometry_pythagorean_tree_v1.json`
- Task module: `trace/tasks/geometry/pythagorean_tree/missing_square_area_value.py`
