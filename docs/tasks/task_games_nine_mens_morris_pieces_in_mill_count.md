# `task_games_nine_mens_morris_pieces_in_mill_count`

## 1) Identity
1. Domain: `games`
2. Task group: `nine_mens_morris`
3. Task id: `task_games_nine_mens_morris_pieces_in_mill_count`
4. Objective: answer one integer counting question about pieces that belong to mills on a visible nine men's morris board.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `white_pieces_in_mill_count`
   - `black_pieces_in_mill_count`
   - `all_pieces_in_mill_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the scene always shows one visible nine men's morris board,
   - light and dark pieces are placed on the labeled board intersections,
   - the board uses the standard `24` intersection geometry,
   - the task counts pieces that belong to at least one completed mill.
7. Query contract:
   - `white_pieces_in_mill_count` asks how many white pieces belong to at least one mill,
   - `black_pieces_in_mill_count` asks how many black pieces belong to at least one mill,
   - `all_pieces_in_mill_count` asks for the total number of pieces of either color that belong to at least one mill.
8. Counting rule:
   - a mill is `3` same-color pieces on one straight board line,
   - count each piece only once even if it belongs to more than one mill.
9. Answer policy:
   - `white_pieces_in_mill_count`: `0|3|5|6|7|8|9`
   - `black_pieces_in_mill_count`: `0|3|5|6|7|8|9`
   - `all_pieces_in_mill_count`: `0|3|5|6|7|8|9|10|11|12|13|14|15|16|17|18`

## 3) Prompt contract
1. Bundle: `games_nine_mens_morris_v1`
2. `task_family_key`: `visible_nine_mens_morris_board`
3. `task_key`: `pieces_in_mill_query`
4. `task_variant_key`: `white_pieces_in_mill_count|black_pieces_in_mill_count|all_pieces_in_mill_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `mill_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/nine_mens_morris.yaml`,
   - deterministic bundle selection from `prompts/games/nine_mens_morris/games_nine_mens_morris_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - define a mill explicitly in every prompt family,
   - state that overlapping mill pieces are counted once,
   - keep the question grounded on the visible board pieces rather than abstract move rules.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the counted pieces:
   - white pieces only for `white_pieces_in_mill_count`,
   - black pieces only for `black_pieces_in_mill_count`,
   - both colors for `all_pieces_in_mill_count`.
2. Zero-count answers use an empty `bbox_set`.
3. `scene_ir.entities` stores one `nine_mens_morris_piece` entity per visible piece.
4. `render_map` includes:
   - `board_bbox_px`
   - `piece_bboxes_px`
   - `node_centers_px`
5. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `target_answer`
   - `target_answer_support`
   - one visible spec per piece (`piece_id`, `node_index`, `node_label`, `color`)
   - `white_piece_ids_in_mill`
   - `black_piece_ids_in_mill`
   - `all_piece_ids_in_mill`
   - `white_mill_ids`
   - `black_mill_ids`
   - `overlapping_piece_ids`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome and piece styling only; they do not change Morris semantics.
3. Prompt-facing evidence stays on piece boxes, not on whole mills or board lines, because the operative witnesses are the counted pieces.
4. Keep white/light and black/dark pieces visually distinct enough that the prompt wording matches the rendered board.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible Morris board.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the feasible support for the chosen query,
   - failure to construct a visible board whose counted pieces-in-mill set matches the requested answer.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `state_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_nine_mens_morris_pieces_in_mill_count_contracts.py`
3. Config tests: `tests/test_games_nine_mens_morris_pieces_in_mill_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
