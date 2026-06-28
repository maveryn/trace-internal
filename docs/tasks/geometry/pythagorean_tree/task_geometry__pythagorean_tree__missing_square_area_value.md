# `task_geometry__pythagorean_tree__missing_square_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `pythagorean_tree`
3. Task id: `task_geometry__pythagorean_tree__missing_square_area_value`
4. Query id: `single`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; each query always asks for three role-bound square-region witnesses)

## Program Contract
- `solve_formula(attached_square_on_right_triangle, visible_inputs=two_side_lengths, unknown_role=marked_square_area, formula_schema=pythagorean_side_relation_then_square_area); scene=pythagorean_tree; scope=missing_square_area_value`

## Query Semantics
- `single` asks for the area of the attached square marked `Area=?`.
- The concrete target square role (`leg_square_1`, `leg_square_2`, or `hypotenuse_square`), integer right-triangle triple, visible side labels, fill palette, font, layout, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/pythagorean_tree/geometry_pythagorean_tree_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `bbox_map` with keys `target_square`, `known_side_1_label`, and `known_side_2_label`. `target_square` is the full attached-square region marked `Area=?`; the side-label boxes are the two visible side-length labels needed to derive the target square area. The private trace keeps the concrete geometric role, such as `leg_square_1`, `leg_square_2`, or `hypotenuse_square`, for verifier/debug metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/pythagorean_tree.yaml`
- Prompt bundle: `prompts/geometry/pythagorean_tree/geometry_pythagorean_tree_v1.json`
- Task module: `trace/tasks/geometry/pythagorean_tree/missing_square_area_value.py`
