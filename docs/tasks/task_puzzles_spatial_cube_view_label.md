# `task_puzzles_spatial_cube_view_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_cube_view_label`
4. V1 goal: choose the labeled option cube that is either a valid or invalid view of the same hinted cube.

## Task variants
1. `same_cube_view`
   - Choose the option that could be another view of the same cube.
2. `impossible_cube_view`
   - Choose the option that cannot be a view of the same cube.

## Scene variants
1. `cube_strip`
2. `cube_card`
3. `cube_outline`

## Contracts
1. Answer type: `answer_gt.type = option_letter`
2. Evidence type: `evidence_gt.type = bbox_set`
3. Evidence cardinality: exactly one bbox
4. Evidence target: the winning option panel bbox

## Scene contract
1. One reference cube appears above one row of option cubes.
2. The reference cube always shows exactly three visible symbol faces.
3. Three explicit opposite-face hint pairs appear between the reference cube and the option row.
4. Exactly six labeled image options (`A` through `F`) appear below the reference cube.
5. The option cubes may show any visible triplet that is consistent or inconsistent with the reference cube plus the opposite-face hints.
6. The prompt asks for the correct option letter, not for the symbol names.

## Trace contract
1. `scene_ir.entities` includes:
   - `puzzle_cube_reference`
   - `puzzle_cube_face`
   - `puzzle_cube_pair_box`
   - `puzzle_cube_pair_token`
   - `puzzle_cube_option_panel`
   - `puzzle_cube_option_label`
   - `puzzle_cube_option_box`
2. `render_map.reference_cube_bbox_px` stores the reference cube bbox.
3. `render_map.pair_box_bboxes_px` stores every opposite-pair hint box bbox keyed by pair-box id.
4. `render_map.option_panel_bboxes_px` stores every option-panel bbox keyed by `option_panel_id`.
5. `render_map.option_cube_bboxes_px` stores every option-cube content bbox keyed by `option_panel_id`.
5. `execution_trace` stores:
   - `reference_view`
   - `face_object_types`
   - `reference_triplet`
   - `opposite_pair_specs`
   - `valid_triplets`
   - `invalid_triplets`
   - `answer_option_label`
   - `correct_option_index`
   - `correct_option_panel_id`
   - `option_specs`
   - `option_count`
   - `visible_face_count`
   - `solver_trace`
6. Prompt-facing evidence is projected from `correct_option_panel_id`, not from pixels.

## Notes
1. V1 keeps the cube-view logic exact by pairing one visible reference view with explicit opposite-face hints, so the option set can safely range over full cube views instead of only the visible corner.
2. The task avoids hidden-face ambiguity by making the hidden-face structure explicit in the image before asking about candidate cube views.
