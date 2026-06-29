# `task_puzzles__tangram__missing_piece_label`

## Program Contract
`label(option_shape == missing_region_shape, rotation_allowed=true, reflection_allowed=false); scene=tangram; scope=missing_piece_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `tangram`
3. Public task id: `task_puzzles__tangram__missing_piece_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_map`

## Annotation
`annotation` is an object with:
- `missing_region`: one image-pixel bounding box for the black missing Tangram region.
- `selected_option`: one image-pixel bounding box for the selected labeled option panel.

## Generation Notes
The correct option may be rotated, but reflected mirror distractors for asymmetric notched pieces are excluded. Option count, option order, style, font, and layout are generation/render metadata, not public query ids.
