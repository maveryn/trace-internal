# `task_games_dots_and_boxes_capture_count`

## 1) Identity
1. Domain: `games`
2. Task group: `dots_and_boxes`
3. Task id: `task_games_dots_and_boxes_capture_count`
4. Objective: answer one integer turn-capture question from a visible dots-and-boxes board with one highlighted starting edge.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `forced_turn_capture_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the scene always shows one visible dots-and-boxes board,
   - some edges are already drawn,
   - one missing edge is highlighted as the starting move,
   - the first version uses a stable `3 x 4` box grid,
   - the generated board guarantees a forced continuation chain after the highlighted move.
7. Query contract:
   - `forced_turn_capture_count` asks for the total number of boxes captured during the turn started by the highlighted edge.
8. Answer policy:
   - `forced_turn_capture_count`: `1..6`

## 3) Prompt contract
1. Bundle: `games_dots_and_boxes_v1`
2. `task_family_key`: `visible_dots_and_boxes_board`
3. `task_key`: `dots_and_boxes_capture_query`
4. `task_variant_key`: `forced_turn_capture_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `forced_turn_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/dots_and_boxes.yaml`,
   - deterministic bundle selection from `prompts/games/dots_and_boxes/games_dots_and_boxes_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - define the bonus-turn rule explicitly in every prompt family,
   - state that the player keeps following the forced box-completing move until the turn ends,
   - keep the question grounded on the highlighted starting edge and visible box grid rather than abstract strategy language.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the boxes captured during the highlighted turn.
2. `scene_ir.entities` stores one `dots_and_boxes_box` entity per visible box plus the highlighted-edge entity.
3. `render_map` includes:
   - `board_bbox_px`
   - `box_bboxes_px`
   - `edge_bboxes_px`
   - `highlighted_edge_id`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `target_answer`
   - `target_answer_support`
   - `box_rows`
   - `box_cols`
   - `highlighted_edge_id`
   - `drawn_edge_ids`
   - `captured_box_ids`
   - `path_box_ids`
   - `move_edge_sequence`
   - `branching_edge_ids`
   - `path_turn_count`
   - one visible spec per edge and per box
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary paper-board chrome and line styling only; they do not change dots-and-boxes semantics.
3. Prompt-facing evidence stays on the captured box regions, not on the highlighted edge, because the operative witnesses are the boxes captured during the turn.
4. Keep the highlighted starting edge visually salient and distinct from already drawn edges.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized forced-turn simulation on the visible board.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the feasible support,
   - failure to construct a visible board whose highlighted move leads to exactly the requested forced-turn capture count,
   - any generated position where the continuation branches instead of remaining forced.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `state_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_dots_and_boxes_capture_count_contracts.py`
3. Config tests: `tests/test_games_dots_and_boxes_capture_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
