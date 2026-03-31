# `task_games_mancala_move_count`

## 1) Identity
1. Domain: `games`
2. Task group: `mancala`
3. Task id: `task_games_mancala_move_count`
4. Objective: answer one integer move-count question from a visible face-up Mancala board.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `midgame_board`
   - `crowded_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `extra_turn_move_count`
   - `capture_move_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - every scene shows one visible Kalah-style Mancala board,
   - the board has six small pits on the top row, six small pits on the bottom row, one left store, and one right store,
   - Blue always controls the bottom row and the right store,
   - Orange always controls the top row and the left store,
   - one visible player badge states that Blue is the player to move,
   - `midgame_board` keeps a lower total visible stone count than `crowded_board`.
7. Query contract:
   - `extra_turn_move_count` asks how many non-empty bottom-row pits would give Blue another turn because the last stone lands in Blue's store,
   - `capture_move_count` asks how many non-empty bottom-row pits would cause Blue to capture stones because the last stone lands in an empty Blue pit opposite a non-empty Orange pit.
8. Answer policy:
   - `extra_turn_move_count`: `0..5`
   - `capture_move_count`: `0..4`

## 3) Prompt contract
1. Bundle: `games_mancala_v1`
2. `task_family_key`: `visible_mancala_board`
3. `task_key`: `mancala_move_query`
4. `task_variant_key`: `extra_turn_move_count|capture_move_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `extra_turn_move_count`: `turn_rule_text`, `extra_turn_rule_text`
     - `capture_move_count`: `turn_rule_text`, `capture_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/mancala.yaml`,
   - deterministic bundle selection from `prompts/games/mancala/games_mancala_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - teach the Blue-side sowing rule directly in the prompt rather than assuming Mancala conventions,
   - state that Blue includes the right store but skips Orange's left store,
   - make the extra-turn and capture rule explicit in the query-specific prompt text.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over bottom-row starting pits:
   - every bottom-row pit that would give Blue another turn for `extra_turn_move_count`,
   - every bottom-row pit that would cause a capture for `capture_move_count`.
2. `scene_ir.entities` stores one `pit` entity per visible pit and one `store` entity per visible store.
3. `render_map` includes:
   - `board_bbox_px`
   - `pit_bboxes_px`
   - `store_bboxes_px`
   - `player_badge_bbox_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `current_player`
   - `target_answer`
   - `target_answer_support`
   - `top_pits`
   - `bottom_pits`
   - `top_store`
   - `bottom_store`
   - `total_stones`
   - `construction_mode`
   - `move_specs`
   - `qualifying_start_indices`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome / badge styling only; they do not change the move semantics.
3. Prompt-facing evidence stays on the starting pits themselves rather than on stores or implied landing locations.
4. The counts shown inside pits and stores should remain large and easy to read; decorative chrome must not obscure the numbers.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible board state.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the configured support,
   - failure to construct a board whose move witness set exactly matches the requested target.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_mancala_move_count_contracts.py`
3. Config tests: `tests/test_games_mancala_move_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
