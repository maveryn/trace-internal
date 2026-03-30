# `task_games_connect_four_move_count`

## 1) Identity
1. Domain: `games`
2. Task group: `connect_four`
3. Task id: `task_games_connect_four_move_count`
4. Objective: answer one integer move-count query from a visible Connect Four board state.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `midgame_board`
   - `crowded_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `winning_move_count`
   - `safe_move_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the visible board is always a standard `7 x 6` Connect Four grid,
   - `midgame_board` keeps a readable midgame density,
   - `crowded_board` keeps a later-game denser position,
   - a visible badge states which player is to move.
7. Query contract:
   - `winning_move_count` asks how many legal drops let the current player win immediately,
   - `safe_move_count` asks how many legal drops leave the opponent without any immediate winning drop on the next turn.
8. Answer policy:
   - `winning_move_count`: `0..4`
   - `safe_move_count`: `0..5`

## 3) Prompt contract
1. Bundle: `games_connect_four_v1`
2. `task_family_key`: `visible_connect_four_board`
3. `task_key`: `connect_four_move_query`
4. `task_variant_key`: `winning_move_count|safe_move_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `winning_move_count`: `current_player_name`, `legal_drop_rule_text`, `winning_rule_text`
     - `safe_move_count`: `current_player_name`, `opponent_player_name`, `legal_drop_rule_text`, `winning_rule_text`, `safety_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/connect_four.yaml`,
   - deterministic bundle selection from `prompts/games/connect_four/games_connect_four_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - explicitly name the current player,
   - state the gravity/drop rule directly in the prompt rather than assuming prior Connect Four knowledge,
   - state the four-in-a-row win condition directly in the prompt,
   - define “safe move” directly in the prompt instead of assuming next-turn threat semantics are obvious.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over board squares:
   - every immediate winning landing square for `winning_move_count`,
   - every safe landing square for `safe_move_count`.
2. `scene_ir.entities` stores one `board_cell` entity per visible square.
3. `render_map` includes:
   - `board_bbox_px`
   - `cell_bboxes_px`
   - `disc_bboxes_px`
   - `player_badge_bbox_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `current_player`
   - `opponent_player`
   - `target_answer`
   - `target_answer_support`
   - `occupied_count`
   - `construction_mode`
   - `board_rows`
   - `winning_move_coords`
   - `safe_move_coords`
   - `evidence_coords`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome / badge / disc styling only; they do not change gameplay semantics.
3. Prompt-facing evidence stays on landing cells, not on columns, arrows, or board chrome.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible board state.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the configured support,
   - failure to construct a board whose legal landing witnesses exactly match the requested target.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_connect_four_move_count_contracts.py`
3. Config tests: `tests/test_games_connect_four_move_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
