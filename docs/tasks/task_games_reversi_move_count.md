# `task_games_reversi_move_count`

## 1) Identity
1. Domain: `games`
2. Task group: `reversi`
3. Task id: `task_games_reversi_move_count`
4. Objective: answer one integer move-count or flip-count question from a visible face-up Reversi board.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `compact_board`
   - `classic_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `legal_move_count`
   - `corner_move_count`
   - `flip_count_for_marked_move`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - `compact_board` shows one visible `6x6` Reversi board,
   - `classic_board` shows one visible `8x8` Reversi board,
   - the board always contains only black discs, white discs, and empty squares,
   - one visible player badge states whose turn it is,
   - `flip_count_for_marked_move` also marks one empty legal destination square with a visible red outline.
7. Query contract:
   - `legal_move_count` asks how many legal moves the current player has,
   - `corner_move_count` asks how many of the current player's legal moves lie on corners,
   - `flip_count_for_marked_move` asks how many discs would flip if the current player plays on the marked square.
8. Answer policy:
   - `legal_move_count`: `0..6`
   - `corner_move_count`: `0..4`
   - `flip_count_for_marked_move`: `1..5`

## 3) Prompt contract
1. Bundle: `games_reversi_v1`
2. `task_family_key`: `visible_reversi_board`
3. `task_key`: `reversi_move_query`
4. `task_variant_key`: `legal_move_count|corner_move_count|flip_count_for_marked_move`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `legal_move_count`: `current_player_name`, `legal_move_rule_text`
     - `corner_move_count`: `current_player_name`, `legal_move_rule_text`, `corner_rule_text`
     - `flip_count_for_marked_move`: `current_player_name`, `legal_move_rule_text`, `marked_move_rule_text`, `flip_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/reversi.yaml`,
   - deterministic bundle selection from `prompts/games/reversi/games_reversi_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - explicitly name the current player,
   - state the legal-move rule directly in the prompt rather than assuming prior Reversi knowledge,
   - identify the marked move explicitly for the flip-count variant.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over board squares:
   - every legal move square for `legal_move_count`,
   - every legal corner move square for `corner_move_count`,
   - every board square containing a disc that would flip for `flip_count_for_marked_move`.
2. `scene_ir.entities` stores one `board_cell` entity per visible square.
3. `render_map` includes:
   - `board_bbox_px`
   - `cell_bboxes_px`
   - `disc_bboxes_px`
   - `player_badge_bbox_px`
   - optional `marked_square_bbox_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `board_size`
   - `current_player`
   - `target_answer`
   - `target_answer_support`
   - `board_rows`
   - `construction_mode`
   - `legal_move_count`
   - `legal_move_specs`
   - optional `marked_move`
   - optional `marked_move_cell_id`
   - optional `marked_move_flip_coords`
   - `evidence_coords`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome / badge / disc styling only; they do not change move semantics.
3. Prompt-facing evidence stays on board squares, not on the badge or board frame.
4. The marked move outline should stay visible without becoming part of the evidence for `flip_count_for_marked_move`.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible board state.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the configured support,
   - failure to construct a board whose legal-move witness set exactly matches the requested target.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_reversi_move_count_contracts.py`
3. Config tests: `tests/test_games_reversi_move_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
