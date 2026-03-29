# `task_puzzles_spatial_fold_result_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_fold_result_label`
4. Objective: choose the labeled option that correctly shows the paper after it is folded along the indicated line.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `vertical_fold_result`
   - `horizontal_fold_result`
2. Supported `scene_variant` values:
   - `fold_strip`
   - `fold_card`
   - `fold_outline`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one paper-fold puzzle per image,
   - one marked square sheet appears above the options,
   - the reference sheet always shows one explicit dashed fold line plus two outside arrows that make the fold direction clear,
   - the reference sheet does not show a visible graph-paper grid; only the reflection-invariant marks are visible on the paper,
   - the options show folded half-sheet results, not unfolded sheets,
   - each option is rendered as a bare folded-paper image with its letter drawn below it, not inside a separate card,
   - vertical-fold variants keep the six options in one row below the reference sheet,
   - horizontal-fold variants use a balanced two-row layout below the reference sheet so the wide folded results stay legible,
   - exactly one option is correct by construction,
   - the number of labeled options is fixed to `6` in the active setup.
6. Generation guarantees:
   - the full paper uses one even square logical grid,
   - every instance uses exactly one fold axis plus one explicit fold direction,
   - the folded result is constructed first, then back-projected onto the original sheet so the reference/result pair stays consistent,
   - at least one visible mark originates from the folded side and at least one visible mark originates from the kept side,
   - all option mark layouts are unique by construction.

## 3) Prompt contract
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_fold_result_puzzle`
3. `task_key`: `fold_result_query`
4. `task_variant_key`: `vertical_fold_result|horizontal_fold_result`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_evidence`
7. Prompt-facing answer is the winning option letter; prompt-facing evidence is the bbox of the winning folded-result option image.
8. Prompt wording should stay explicit that the paper is folded along the dashed line in the direction of the outside arrows.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item: the bbox of the correct option image.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_fold_reference_panel`
   - `puzzle_fold_reference_paper`
   - `puzzle_fold_line`
   - `puzzle_fold_arrow`
   - `puzzle_fold_mark`
   - `puzzle_fold_option_choice`
   - `puzzle_fold_option_label`
   - `puzzle_fold_result_paper`
4. `render_map` includes:
   - `scene_bbox_px`
   - `reference_panel_bbox_px`
   - `reference_paper_bbox_px`
   - `option_choice_bboxes_px`
5. `execution_trace` records:
   - `fold_axis`
   - `fold_direction`
   - `grid_size`
   - `result_grid_cols`
   - `result_grid_rows`
   - `mark_count`
   - `folded_mark_count`
   - `kept_mark_count`
   - `original_mark_specs`
   - `folded_result_mark_specs`
   - `option_specs`
   - `correct_option_choice_id`
   - `correct_option_index`
   - `solver_trace`

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 fold-result puzzles use clean light backgrounds, one explicit dashed fold line, and outside arrows so the fold direction is visible without covering the paper.
3. Scene variants change framing and outer panel chrome while preserving the same one-sheet plus options grammar.
4. The reference sheet and option sheets should remain visually legible without relying on hidden paper-side or mirrored-symbol conventions.
5. The fold renderer uses supersampled drawing before downsampling so the paper edges, symbols, and arrows stay less jagged in the final image.

## 6) Determinism + constraints
1. Deterministic sampling and rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated fold-result scene.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded winning option-image projection, not OCR or visual guesswork.
