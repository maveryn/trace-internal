# Puzzle Task Setup

## Purpose
Capture the active v1 contract for the `puzzles` domain.

## Active families
1. Current active `task_group` values:
   - `arithmetic`
   - `logic`
   - `spatial`
2. Current active tasks:
   - `task_puzzles_arithmetic_equation_value`
   - `task_puzzles_arithmetic_balance_value`
   - `task_puzzles_arithmetic_grid_value`
   - `task_puzzles_logic_grid_completion_label`
   - `task_puzzles_spatial_fold_result_label`
   - `task_puzzles_spatial_cube_removal_count`

## Family contract
1. Puzzle families are hidden-rule / hidden-variable reasoning families, not generic icon grids or mini tables.
2. The active arithmetic family centers on explicit local query targets so the prompt-facing evidence can stay local and simple.
3. The active logic family currently centers on one missing grid cell plus six labeled image options, so the answer format can stay `option_letter` while the evidence stays local to one option panel.
4. The active spatial family currently mixes option-based fold-result puzzles and integer cube-removal comparison puzzles, while keeping the prompt-facing evidence local to one winning option image or one ordered pair of visible structure regions.
5. Puzzle variants should widen `task_variant` before creating a new task id when the same scene grammar and evidence contract still hold.

## `task_puzzles_arithmetic_equation_value`
1. Supported `task_variant` values:
   - `result_unknown`
   - `operand_unknown`
2. Supported `scene_variant` values:
   - `equation_strip`
   - `equation_card`
   - `equation_outline`
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the explicit question-mark slot
5. Scene contract:
   - one arithmetic puzzle per image,
   - exactly one equation row,
   - `2..5` boxed values on the left side of the equation by default,
   - one boxed result on the right side of the equation,
   - `3..6` visible boxed slots in total by default,
   - every variant includes exactly one explicit unknown slot rendered as `?`,
   - visible operands and result values are integers,
   - arithmetic operators are sampled from `+`, `-`, and `×`,
   - the answer is the integer that belongs in the unknown slot.
6. Trace contract:
   - `scene_ir.entities` includes slot and operator entities,
   - `render_map.slot_bboxes_px` stores each slot bbox keyed by slot id,
   - `execution_trace` stores `equation_rows`, `solver_trace`, `query_slot_id`, `slot_count`, `slot_count_range`, `operand_count`, `operand_count_range`, and `step_count`,
   - prompt-facing evidence is projected from `query_slot_id`, not inferred from pixels.

## `task_puzzles_arithmetic_balance_value`
1. Supported `task_variant` values:
   - `sum_pair_unknown`
   - `two_panel_chain_unknown`
   - `three_panel_chain_unknown`
2. Supported `scene_variant` values:
   - `balance_strip`
   - `balance_card`
   - `balance_outline`
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the question-mark query box
5. Scene contract:
   - one arithmetic equality puzzle per image,
   - `2..3` stacked equality panels with boxed symbols and/or boxed integers,
   - explicit plus signs appear between multiple items on the same side of a panel,
   - panel rows may use small deterministic spacing jitter while keeping the local operator/equality spacing visually balanced,
   - one final query row below the panels has the form `symbol = ?`,
   - every variant keeps the queried symbol local to that final query row,
   - the answer is the integer value that replaces the question mark.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_balance_box`, `puzzle_balance_operator`, `puzzle_balance_equals`, and `puzzle_balance_panel` entities,
   - `render_map.box_bboxes_px` stores each panel/query box bbox keyed by box id,
   - `execution_trace` stores `panel_specs`, `solver_trace`, `query_box_id`, `query_object_box_id`, `query_object_type`, `panel_count`, `panel_count_range`, `total_box_count`, `total_box_count_range`, `panel_relation_gap_offsets_px`, and `relation_gap_jitter_range_px`,
   - prompt-facing evidence is projected from `query_box_id`, not inferred from pixels.

## `task_puzzles_arithmetic_grid_value`
1. Supported `task_variant` values:
   - `sum_rule_missing`
   - `difference_rule_missing`
   - `product_rule_missing`
2. Supported `scene_variant` values:
   - `grid_strip`
   - `grid_card`
   - `grid_outline`
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the explicit question-mark grid cell
5. Scene contract:
   - one arithmetic number grid per image,
   - `3..5` rows by default,
   - exactly `3` columns in v1,
   - no headers or axis-like labels,
   - every fully visible row follows the same hidden rule `a op b = c`,
   - the answer is the integer that belongs in the unknown cell.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_grid_cell` entities,
   - `render_map.cell_bboxes_px` stores each grid-cell bbox keyed by cell id,
   - `execution_trace` stores `grid_rows`, `row_values`, `visible_example_rows`, `solver_trace`, `query_cell_id`, `query_row_index`, `query_col_index`, `row_count`, `row_count_range`, `cell_count`, and `cell_count_range`,
   - prompt-facing evidence is projected from `query_cell_id`, not inferred from pixels.

## `task_puzzles_logic_grid_completion_label`
1. Supported `task_variant` values:
   - `row_uniqueness`
   - `column_uniqueness`
   - `row_and_column_uniqueness`
2. Supported `scene_variant` values:
   - `logic_strip`
   - `logic_card`
   - `logic_outline`
3. Answer contract:
   - `answer_gt.type = option_letter`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning option panel
5. Scene contract:
   - one square logic grid per image,
   - board size ranges from `3x3` through `5x5`,
   - exactly one board cell shows `?`,
   - exactly six labeled image options (`A..F`) appear below the board,
   - each option panel contains one candidate shape,
   - the answer is the option letter, not the shape name.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_logic_cell`, `puzzle_logic_option_panel`, `puzzle_logic_option_label`, and `puzzle_logic_option_symbol_box` entities,
   - `render_map.cell_bboxes_px` stores each board-cell bbox keyed by `cell_id`,
   - `render_map.option_panel_bboxes_px` stores each option-panel bbox keyed by `option_panel_id`,
   - `execution_trace` stores `board_values`, `grid_rows`, `symbol_pool`, `query_cell_id`, `query_row_index`, `query_col_index`, `answer_object_type`, `answer_option_label`, `correct_option_index`, `correct_option_panel_id`, `option_specs`, `board_size`, `board_size_range`, `cell_count`, `cell_count_range`, `option_count`, and `solver_trace`,
   - prompt-facing evidence is projected from `correct_option_panel_id`, not inferred from pixels.

## `task_puzzles_spatial_fold_result_label`
1. Supported `task_variant` values:
   - `vertical_fold_result`
   - `horizontal_fold_result`
2. Supported `scene_variant` values:
   - `fold_strip`
   - `fold_card`
   - `fold_outline`
3. Answer contract:
   - `answer_gt.type = option_letter`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning option image
5. Scene contract:
   - one paper-fold result puzzle per image,
   - one marked square paper sheet appears above the options,
   - the reference sheet always shows one explicit dashed fold line and two fold-direction arrows outside the paper,
   - the reference sheet does not show visible graph-paper grid lines,
   - exactly six labeled folded-result options appear below the reference sheet,
   - each option shows one folded half-sheet with candidate mark positions and its letter beneath the image,
   - vertical folds keep the six narrow options in one row,
   - horizontal folds use a balanced two-row arrangement so the wide folded sheets stay readable,
   - the answer is the option letter, not a free-form view description.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_fold_reference_panel`, `puzzle_fold_reference_paper`, `puzzle_fold_line`, `puzzle_fold_arrow`, `puzzle_fold_mark`, `puzzle_fold_option_choice`, `puzzle_fold_option_label`, and `puzzle_fold_result_paper` entities,
   - `render_map.reference_panel_bbox_px` stores the full reference-panel bbox,
   - `render_map.reference_paper_bbox_px` stores the reference paper bbox,
   - `render_map.option_choice_bboxes_px` stores each option-image bbox keyed by `option_choice_id`,
   - `execution_trace` stores `fold_axis`, `fold_direction`, `grid_size`, `result_grid_cols`, `result_grid_rows`, `mark_count`, `folded_mark_count`, `kept_mark_count`, `original_mark_specs`, `folded_result_mark_specs`, `answer_option_label`, `correct_option_index`, `correct_option_choice_id`, `option_specs`, `option_count`, and `solver_trace`,
   - prompt-facing evidence is projected from `correct_option_choice_id`, not inferred from pixels.

## `task_puzzles_spatial_cube_removal_count`
1. Supported `task_variant` values:
   - `cube_removal_count`
2. Supported `scene_variant` values:
   - `stack_strip`
   - `stack_card`
   - `stack_outline`
3. Answer contract:
   - `answer_gt.type = integer`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly two bboxes ordered `[original block on the left, remaining block on the right]`
5. Scene contract:
   - one fixed-view isometric block comparison per image,
   - the left structure is the original block and the right structure is the remaining block after cubes were removed,
   - both structures share the same viewpoint and shared rendering scale,
   - only visible cube faces are rendered in the image and the removed cubes remain implicit,
   - the prompt asks for the number of cubes taken from the original block,
   - the answer is that removal count as an integer.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_block_structure`, `puzzle_block_caption`, `puzzle_block_arrow`, and `puzzle_block_face` entities,
   - `render_map.original_structure_bbox_px` and `render_map.remaining_structure_bbox_px` store the projected bboxes for the two visible structures,
   - `render_map.structure_bboxes_px` stores visible structure regions keyed by `structure_bbox_id`,
   - `execution_trace` stores `original_height_rows`, `remaining_height_rows`, `row_count`, `col_count`, `original_max_height`, `original_total_cubes`, `remaining_total_cubes`, `removal_count`, `changed_column_count`, `original_cube_records`, `remaining_cube_records`, `removed_cube_records`, `original_structure_bbox_id`, `remaining_structure_bbox_id`, `supporting_structure_ids`, and `solver_trace`,
   - prompt-facing evidence is projected from the ordered visible structure ids, not from fake removed-cube image boxes.

## Prompt contract for `task_puzzles_arithmetic_equation_value`
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_unknown_slot_puzzle`
3. `task_key`: `equation_value_query`
4. `task_variant_key`: `result_unknown|operand_unknown`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the question-mark slot.

## Prompt contract for `task_puzzles_arithmetic_balance_value`
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_balance_query_puzzle`
3. `task_key`: `balance_value_query`
4. `task_variant_key`: `sum_pair_unknown|two_panel_chain_unknown|three_panel_chain_unknown`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the final question-mark query box.

## Prompt contract for `task_puzzles_arithmetic_grid_value`
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_grid_unknown_puzzle`
3. `task_key`: `grid_value_query`
4. `task_variant_key`: `sum_rule_missing|difference_rule_missing|product_rule_missing`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the question-mark grid cell.

## Prompt contract for `task_puzzles_logic_grid_completion_label`
1. Bundle: `puzzles_logic_v1`
2. `task_family_key`: `logic_option_completion_puzzle`
3. `task_key`: `grid_completion_query`
4. `task_variant_key`: `row_uniqueness|column_uniqueness|row_and_column_uniqueness`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option image.

## Prompt contract for `task_puzzles_spatial_fold_result_label`
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_fold_result_puzzle`
3. `task_key`: `fold_result_query`
4. `task_variant_key`: `vertical_fold_result|horizontal_fold_result`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option image.

## Prompt contract for `task_puzzles_spatial_cube_removal_count`
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_cube_removal_puzzle`
3. `task_key`: `cube_removal_count_query`
4. `task_variant_key`: `cube_removal_count`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the two-box contract explicit: the returned bboxes are ordered `[original block on the left, remaining block on the right]`.

## Visual policy
1. Puzzles use the same light solid background baseline as the other clean synthetic domains.
2. Arithmetic scene variants vary panel chrome and outline treatment, not the semantic layouts of the equation row, equality panels, or arithmetic grids.
3. The equation unknown slot, equality query answer box, arithmetic-grid question-mark cell, logic-grid winning option panel, spatial fold-result winning option image, and hidden-cube visible structure should stay visually salient relative to the other boxes.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated puzzle has exactly one valid integer answer.
4. Review/sample overlays should use the recorded bbox maps (`render_map.slot_bboxes_px[query_slot_id]`, `render_map.box_bboxes_px[query_box_id]`, `render_map.cell_bboxes_px[query_cell_id]`, `render_map.option_panel_bboxes_px[correct_option_panel_id]`, `render_map.option_choice_bboxes_px[correct_option_choice_id]`, or `render_map.structure_bboxes_px[structure_bbox_id]`) for the prompt-facing witness.
