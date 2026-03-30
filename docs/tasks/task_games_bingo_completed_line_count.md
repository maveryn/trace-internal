# `task_games_bingo_completed_line_count`

## 1) Identity
1. Domain: `games`
2. Task group: `bingo`
3. Task id: `task_games_bingo_completed_line_count`
4. Objective: answer one integer completed-line counting question from a visible `5 x 5` bingo card.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_card`
2. Supported `query_variant` / emitted `task_variant` values:
   - `completed_row_count`
   - `completed_column_count`
   - `completed_straight_line_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the scene always shows one face-up `5 x 5` bingo card,
   - the visible card has `B I N G O` column headers and one number in every cell,
   - some cells are visibly marked,
   - the first version has no free center cell,
   - `completed_straight_line_count` counts rows and columns only, not diagonals.
7. Query contract:
   - `completed_row_count` asks how many rows have all five cells marked,
   - `completed_column_count` asks how many columns have all five cells marked,
   - `completed_straight_line_count` asks how many rows or columns are fully marked.
8. Answer policy:
   - `completed_row_count`: `0..5`
   - `completed_column_count`: `0..5`
   - `completed_straight_line_count`: `0..8`

## 3) Prompt contract
1. Bundle: `games_bingo_v1`
2. `task_family_key`: `visible_bingo_card`
3. `task_key`: `bingo_completed_line_query`
4. `task_variant_key`: `completed_row_count|completed_column_count|completed_straight_line_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `completed_row_count`: `completed_row_rule_text`
     - `completed_column_count`: `completed_column_rule_text`
     - `completed_straight_line_count`: `completed_straight_line_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/bingo.yaml`,
   - deterministic bundle selection from `prompts/games/bingo/games_bingo_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - define “completed” explicitly in every prompt family,
   - keep rows/columns semantics explicit,
   - keep the prompt grounded on visible marked cells rather than abstract bingo rules.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the marked cells that belong to the counted completed lines:
   - all marked cells in completed rows for `completed_row_count`,
   - all marked cells in completed columns for `completed_column_count`,
   - all marked cells in completed rows or columns for `completed_straight_line_count`.
2. Zero-count answers use an empty `bbox_set`.
3. `scene_ir.entities` stores one `bingo_cell` entity per visible cell.
4. `render_map` includes:
   - `card_bbox_px`
   - `column_header_bboxes_px`
   - `cell_bboxes_px`
   - `cell_mark_centers_px`
5. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `target_answer`
   - `target_answer_support`
   - `numbers_grid`
   - `mark_grid`
   - `completed_row_indices`
   - `completed_column_indices`
   - one visible spec per cell (`row_index`, `column_index`, `column_label`, `number`, `is_marked`)
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary card chrome and mark styling only; they do not change bingo semantics.
3. Prompt-facing evidence stays on cell boxes, not on the whole card, because the operative witnesses are the marked cells themselves.
4. Keep the marked cells visually salient enough that completed lines are readable without widening evidence to headers or the full board.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible bingo card.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the feasible support for the chosen query,
   - failure to construct a visible card whose completed-line count matches the requested answer.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `state_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_bingo_completed_line_count_contracts.py`
3. Config tests: `tests/test_games_bingo_completed_line_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
