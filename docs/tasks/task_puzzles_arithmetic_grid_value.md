# `task_puzzles_arithmetic_grid_value`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `arithmetic`
3. Task id: `task_puzzles_arithmetic_grid_value`
4. Objective: answer the exact integer that should fill the explicit unknown cell in a visual arithmetic rule grid.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `sum_rule_missing`
   - `difference_rule_missing`
   - `product_rule_missing`
2. Supported `scene_variant` values:
   - `grid_strip`
   - `grid_card`
   - `grid_outline`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one arithmetic puzzle grid per image,
   - `3..5` rows by default,
   - exactly `3` columns in v1,
   - boxed integer cells only, with no row or column headers,
   - exactly one explicit unknown cell rendered as `?`,
   - each fully visible row follows the same arithmetic rule `a op b = c`,
   - the hidden cell may appear in either operand column or the result column,
   - the answer is the integer that belongs in the unknown cell.
6. Generation guarantees:
   - at least two fully visible example rows remain after hiding the query cell,
   - all fully visible rows support exactly one active operator family from `+`, `-`, and `×`,
   - all visible cell values and the hidden answer stay within the configured answer bounds by default,
   - the hidden cell is unique by construction.

## 3) Prompt contract
1. Bundle: `puzzles_arithmetic_v1`
2. `task_family_key`: `arithmetic_grid_unknown_puzzle`
3. `task_key`: `grid_value_query`
4. `task_variant_key`: `sum_rule_missing|difference_rule_missing|product_rule_missing`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/arithmetic.yaml`,
   - deterministic bundle selection from `prompts/puzzles/arithmetic/puzzles_arithmetic_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the missing integer; prompt-facing evidence is the bbox for the explicit question-mark cell.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item: the bbox of the unknown grid cell.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_grid_cell` entities for all visible and unknown cells
4. `render_map` includes:
   - `scene_bbox_px`
   - `cell_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `grid_rows`
   - `row_values`
   - `visible_example_rows`
   - `solver_trace`
   - `query_cell_id`
   - `query_row_index`
   - `query_col_index`
   - `row_count`
   - `row_count_range`
   - `cell_count`
   - `cell_count_range`
   - final integer answer

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 arithmetic grid puzzles use clean light solid backgrounds only.
3. Scene variants change framing and outline treatment while preserving the same numeric-grid geometry contract.
4. The question-mark cell stays visually highlighted relative to the known numeric cells.
5. The grid should read as a puzzle board rather than a table, so no headers or axis-like labels are rendered.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated grid scene.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded `query_cell_id` projection, not OCR from pixels.
