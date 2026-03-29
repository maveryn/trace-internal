# `task_puzzles_spatial_fold_hole_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_fold_hole_label`
4. Objective: choose the labeled option that correctly shows the paper after it is unfolded.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `single_fold_single_hole`
   - `single_fold_two_holes`
   - `double_fold_single_hole`
2. Supported `scene_variant` values:
   - `fold_strip`
   - `fold_card`
   - `fold_outline`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one folded-paper hole-punch puzzle per image,
   - three reference step panels appear above the options,
   - the first step always shows one explicit fold line and one fold-direction arrow,
   - the final step always shows the folded packet with one or two visible punched holes,
   - the options show full unfolded square sheets with candidate hole patterns,
   - exactly one option is correct by construction,
   - the number of labeled options is fixed to `6` in the active setup.
6. Generation guarantees:
   - the full paper uses one even square logical grid,
   - fold directions are explicit in the image rather than implicit,
   - folded holes unfold by deterministic reflection across the active fold axis or axes,
   - all option hole patterns are unique by construction.

## 3) Prompt contract
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_fold_hole_puzzle`
3. `task_key`: `unfold_query`
4. `task_variant_key`: `single_fold_single_hole|single_fold_two_holes|double_fold_single_hole`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_evidence`
7. Prompt-facing answer is the winning option letter; prompt-facing evidence is the bbox of the winning option panel.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item: the bbox of the correct option panel.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_fold_step_panel` entities for the three reference steps,
   - `puzzle_option_panel` entities for the labeled options,
   - `puzzle_fold_hole` entities for punched-hole marks in the folded packet and the options.
4. `render_map` includes:
   - `scene_bbox_px`
   - `reference_panel_bbox_px`
   - `step_panel_bboxes_px`
   - `option_panel_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `fold_mode`
   - `fold_axes`
   - `grid_size`
   - `punch_count`
   - `folded_hole_cells`
   - `unfolded_hole_cells`
   - `option_specs`
   - `correct_option_panel_id`
   - `correct_option_index`
   - `solver_trace`

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 fold-hole puzzles use clean light backgrounds and explicit fold arrows.
3. Scene variants change framing and panel chrome while preserving the same three-step reference plus options layout.
4. The folded packet and the final punched holes should remain visually obvious in the last reference step.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated fold-hole scene.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded winning option panel projection, not OCR or visual guesswork.
