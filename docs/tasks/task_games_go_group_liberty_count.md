# `task_games_go_group_liberty_count`

## 1) Identity
1. Domain: `games`
2. Task group: `go`
3. Task id: `task_games_go_group_liberty_count`
4. Objective: answer one integer counting question about the liberties of one highlighted group on a visible `7 x 7` Go board.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `open_board`
   - `crowded_board`
2. Supported `query_variant` / emitted `task_variant` values:
   - `marked_black_group_liberty_count`
   - `marked_white_group_liberty_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the scene always shows one visible `7 x 7` Go board,
   - one connected same-color group is highlighted with a blue outline,
   - the board may be relatively open or visually crowded, but the highlighted group and its neighboring intersections stay readable,
   - no hidden stones or off-board information are needed.
7. Query contract:
   - `marked_black_group_liberty_count` asks for the liberties of the highlighted black group,
   - `marked_white_group_liberty_count` asks for the liberties of the highlighted white group.
8. Counting rule:
   - same-color stones that touch edge to edge form one group,
   - a liberty is an empty intersection directly above, below, left, or right of any stone in the group,
   - diagonal intersections do not count.
9. Answer policy:
   - supported answers: `1|2|3|4|5|6|7|8`

## 3) Prompt contract
1. Bundle: `games_go_v1`
2. `task_family_key`: `visible_go_board`
3. `task_key`: `go_group_liberty_query`
4. `task_variant_key`: `marked_black_group_liberty_count|marked_white_group_liberty_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `marked_group_rule_text`, `group_rule_text`, `liberty_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/go.yaml`,
   - deterministic bundle selection from `prompts/games/go/games_go_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - define both `group` and `liberty` explicitly in every prompt family,
   - keep the board size fixed to `7 x 7`,
   - make the highlighted queried group explicit so the task stays local to visible state.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the empty liberty intersections of the highlighted group.
2. `scene_ir.entities` stores one `go_intersection` entity per visible board intersection, including occupancy, highlighted-group membership, and liberty flags.
3. `render_map` includes:
   - `board_bbox_px`
   - `inner_board_bbox_px`
   - `point_centers_px`
   - `point_bboxes_px`
   - `stone_bboxes_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `board_size`
   - `marked_group_color`
   - `target_answer`
   - `target_answer_support`
   - one visible spec per stone (`stone_id`, `point_id`, `row`, `col`, `color`, `is_marked_group`)
   - `marked_group_coords`
   - `marked_group_point_ids`
   - `liberty_coords`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary board chrome and stone styling only; they do not change Go semantics.
3. Prompt-facing evidence stays on the empty liberty intersections rather than on the highlighted stones, because the counted witnesses are the liberties themselves.
4. The highlighted queried group should stay visually obvious without pre-highlighting the liberties.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible board.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the configured support,
   - failure to construct a visible `7 x 7` board whose highlighted group has exactly the requested liberty count,
   - sampled extra stones that would create a zero-liberty group anywhere on the visible board.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `state_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_go_group_liberty_count_contracts.py`
3. Config tests: `tests/test_games_go_group_liberty_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
