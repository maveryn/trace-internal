# `task_puzzles_spatial_overlay_result_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_overlay_result_label`
4. Objective: choose the labeled result image that matches the combined pattern formed by overlaying two aligned transparent sheets.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `overlay_union_same_grid`
2. Supported `scene_variant` values:
   - `overlay_strip`
   - `overlay_card`
   - `overlay_outline`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one transparent-sheet overlay puzzle per image,
   - two aligned source sheets appear above the options,
   - the two source sheets always share the same visible paper frame and hidden grid alignment,
   - `5..6` labeled result options appear below the source sheets,
   - the prompt explicitly says the sheets are placed exactly on top of each other,
   - the prompt explicitly says no rotation or flipping is allowed,
   - the answer is the letter of the one correct combined result.
6. Generation guarantees:
   - source sheets default to `4..5` hidden grid cells per side,
   - each source sheet defaults to `2..5` visible marks,
   - the two source sheets share `1..2` overlapping marks by default,
   - the active rule is union: any mark present on either sheet appears in the result,
   - exactly one option matches the correct combined result in every accepted scene.

## 3) Prompt contract
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_overlay_puzzle`
3. `task_key`: `overlay_result_query`
4. `task_variant_key`: `overlay_union_same_grid`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/spatial.yaml`,
   - deterministic bundle selection from `prompts/puzzles/spatial/puzzles_spatial_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the option letter; prompt-facing evidence is the winning option image bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item:
   - the correct option image bbox.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_overlay_reference_panel`
   - `puzzle_overlay_source_sheet`
   - `puzzle_overlay_operator`
   - `puzzle_overlay_mark`
   - `puzzle_overlay_option_choice`
   - `puzzle_overlay_option_label`
   - `puzzle_overlay_option_paper`
   - `puzzle_overlay_option_mark`
4. `render_map` includes:
   - `scene_bbox_px`
   - `reference_panel_bbox_px`
   - `source_sheet_bboxes_px`
   - `option_choice_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `grid_size`
   - `grid_size_range`
   - `option_count`
   - `option_count_range`
   - `sheet_mark_count_range`
   - `overlap_count_range`
   - `left_cells`
   - `right_cells`
   - `overlap_cells`
   - `union_cells`
   - `left_mark_specs`
   - `right_mark_specs`
   - `left_mark_count`
   - `right_mark_count`
   - `overlap_count`
   - `union_mark_count`
   - `option_specs`
   - `answer_option_label`
   - `correct_option_index`
   - `correct_option_choice_id`
   - `supporting_option_choice_ids`
   - `solver_trace`
6. Prompt-facing evidence is projected from `correct_option_choice_id`, not from the source sheets.

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 overlay scenes use the same paper size and the same hidden-grid alignment for both source sheets and all option images so the task tests superposition instead of hidden rescaling or translation.
3. Scene variants only change outer panel chrome while preserving the same two-source / options-below layout.
4. The source sheets and the options use the same mark style and the same paper geometry so the task reads as one consistent overlay grammar.
5. Prompt-facing evidence should align to the winning option image, not to the source sheets.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact overlay construction.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded winning option-image projection, not perceptual matching from pixels.
