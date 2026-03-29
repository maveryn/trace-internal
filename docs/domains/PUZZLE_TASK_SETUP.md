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
   - `task_puzzles_spatial_fold_hole_label`

## Family contract
1. Puzzle families are hidden-rule / hidden-variable reasoning families, not generic icon grids or mini tables.
2. The active arithmetic family centers on explicit local query targets so the prompt-facing evidence can stay local and simple.
3. The active logic family currently centers on one missing grid cell plus six labeled image options, so the answer format can stay `option_letter` while the evidence stays local to one option panel.
4. The active spatial family currently centers on explicit fold-diagram plus options tasks, so the answer format can stay `option_letter` while the evidence stays local to one winning option panel.
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

## `task_puzzles_spatial_fold_hole_label`
1. Supported `task_variant` values:
   - `single_fold_single_hole`
   - `single_fold_two_holes`
   - `double_fold_single_hole`
2. Supported `scene_variant` values:
   - `fold_strip`
   - `fold_card`
   - `fold_outline`
3. Answer contract:
   - `answer_gt.type = option_letter`
4. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning option panel
5. Scene contract:
   - one folded-paper hole-punch puzzle per image,
   - exactly three reference step panels appear above the options,
   - the first visible step always shows one explicit fold line and one fold-direction arrow,
   - the final visible step always shows the folded packet with the punched holes,
   - exactly six labeled unfolded-paper options appear below the reference steps,
   - each option panel shows one full square sheet with candidate hole positions,
   - the answer is the option letter, not a free-form view description.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_fold_step_panel`, `puzzle_option_panel`, and `puzzle_fold_hole` entities,
   - `render_map.reference_panel_bbox_px` stores the full reference-panel bbox,
   - `render_map.step_panel_bboxes_px` stores each reference-step bbox keyed by step id,
   - `render_map.option_panel_bboxes_px` stores each option-panel bbox keyed by `option_panel_id`,
   - `execution_trace` stores `fold_mode`, `fold_axes`, `grid_size`, `punch_count`, `folded_hole_cells`, `unfolded_hole_cells`, `answer_option_label`, `correct_option_index`, `correct_option_panel_id`, `option_specs`, `option_count`, and `solver_trace`,
   - prompt-facing evidence is projected from `correct_option_panel_id`, not inferred from pixels.

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
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option panel.

## Prompt contract for `task_puzzles_spatial_fold_hole_label`
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_fold_hole_puzzle`
3. `task_key`: `unfold_query`
4. `task_variant_key`: `single_fold_single_hole|single_fold_two_holes|double_fold_single_hole`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option panel.

## Visual policy
1. Puzzles use the same light solid background baseline as the other clean synthetic domains.
2. Arithmetic scene variants vary panel chrome and outline treatment, not the semantic layouts of the equation row, equality panels, or arithmetic grids.
3. The equation unknown slot, equality query answer box, arithmetic-grid question-mark cell, logic-grid winning option panel, and spatial fold-hole winning option panel should stay visually salient relative to the other boxes.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated puzzle has exactly one valid integer answer.
4. Review/sample overlays should use the recorded bbox maps (`render_map.slot_bboxes_px[query_slot_id]`, `render_map.box_bboxes_px[query_box_id]`, `render_map.cell_bboxes_px[query_cell_id]`, or `render_map.option_panel_bboxes_px[correct_option_panel_id]`) for the prompt-facing witness.
