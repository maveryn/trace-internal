# Puzzle Task Setup

## Purpose
Capture the active v1 contract for the `puzzles` domain.

## Active family
1. Current active `task_group`: `arithmetic`
2. Current active tasks:
   - `task_puzzles_arithmetic_equation_value`
   - `task_puzzles_arithmetic_balance_value`
   - `task_puzzles_arithmetic_grid_value`

## Family contract
1. Puzzle families are hidden-rule / hidden-variable reasoning families, not generic icon grids or mini tables.
2. The active arithmetic family centers on explicit local query targets so the prompt-facing evidence can stay local and simple.
3. Arithmetic puzzle variants should widen `task_variant` before creating a new task id when the same scene grammar and one-box evidence contract still hold.

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
   - exactly one bbox for the highlighted query box
5. Scene contract:
   - one arithmetic equality puzzle per image,
   - `2..3` stacked equality panels with boxed symbols and/or boxed integers,
   - one highlighted query box below the panels,
   - every variant keeps the queried symbol local to that highlighted query box,
   - the answer is the integer value of the highlighted query symbol.
6. Trace contract:
   - `scene_ir.entities` includes `puzzle_balance_box`, `puzzle_balance_equals`, and `puzzle_balance_panel` entities,
   - `render_map.box_bboxes_px` stores each panel/query box bbox keyed by box id,
   - `execution_trace` stores `panel_specs`, `solver_trace`, `query_box_id`, `query_object_type`, `panel_count`, `panel_count_range`, `total_box_count`, and `total_box_count_range`,
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

## Prompt contract
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
6. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the highlighted query box.

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

## Visual policy
1. Puzzles use the same light solid background baseline as the other clean synthetic domains.
2. Arithmetic scene variants vary panel chrome and outline treatment, not the semantic layouts of the equation row, equality panels, or arithmetic grids.
3. The equation unknown slot, equality query box, and arithmetic-grid question-mark cell should stay visually salient relative to the other boxes.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated puzzle has exactly one valid integer answer.
4. Review/sample overlays should use the recorded bbox maps (`render_map.slot_bboxes_px[query_slot_id]`, `render_map.box_bboxes_px[query_box_id]`, or `render_map.cell_bboxes_px[query_cell_id]`) for the prompt-facing witness.
