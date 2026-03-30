# `task_games_checkers_move_count`

## 1) Identity
1. Domain: `games`
2. Task group: `checkers`
3. Task id: `task_games_checkers_move_count`
4. Objective: answer one integer move-count question from a visible face-up checkers board.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `midgame_board`
   - `crowded_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `legal_move_count`
   - `capture_move_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - every scene shows one visible `8x8` board,
   - only the dark squares are playable,
   - all shown pieces are ordinary men rather than kings,
   - `midgame_board` keeps a looser piece density,
   - `crowded_board` keeps a denser piece density,
   - one visible player badge states whose turn it is.
7. Query contract:
   - `legal_move_count` asks how many single-step legal moves the current player has when ordinary diagonal steps and single captures both count as legal moves,
   - `capture_move_count` asks how many legal single-jump captures the current player has,
   - multi-jump continuations after the first landing are always ignored.
8. Answer policy:
   - `legal_move_count`: `0..5`
   - `capture_move_count`: `0..4`

## 3) Prompt contract
1. Bundle: `games_checkers_v1`
2. `task_family_key`: `visible_checkers_board`
3. `task_key`: `checkers_move_query`
4. `task_variant_key`: `legal_move_count|capture_move_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `legal_move_count`: `current_player_name`, `movement_rule_text`, `capture_rule_text`, `single_jump_rule_text`, `legal_move_rule_text`
     - `capture_move_count`: `current_player_name`, `movement_rule_text`, `capture_rule_text`, `single_jump_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/checkers.yaml`,
   - deterministic bundle selection from `prompts/games/checkers/games_checkers_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - explicitly name the current player,
   - explain movement direction directly in the prompt instead of assuming board orientation conventions,
   - state the single-jump capture rule directly in the prompt,
   - state that captures are not mandatory for the `legal_move_count` variant.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over landing squares:
   - every legal landing square for `legal_move_count`,
   - every legal capture landing square for `capture_move_count`.
2. The task constrains every counted move to a unique landing square by construction, so each evidence box corresponds to exactly one counted move.
3. `scene_ir.entities` stores one `board_cell` entity per visible square and one `checker_piece` entity per visible piece.
4. `render_map` includes:
   - `board_bbox_px`
   - `cell_bboxes_px`
   - `piece_bboxes_px`
   - `player_badge_bbox_px`
5. `execution_trace` records:
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
   - `occupied_count`
   - `legal_move_count`
   - `capture_move_count`
   - `legal_move_specs`
   - `evidence_coords`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome / badge / piece styling only; they do not change move semantics.
3. Prompt-facing evidence stays on landing squares rather than entire rows, diagonals, or piece boxes.
4. The board should remain easy to read as checkers rather than chess: no crowns, no coordinate labels, and no hidden pieces.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible board state.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the configured support,
   - failure to construct a board whose move witness set exactly matches the requested target,
   - any counted move set whose landing squares are not unique.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_checkers_move_count_contracts.py`
3. Config tests: `tests/test_games_checkers_move_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
