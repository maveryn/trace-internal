# `task_games_cards_hand_count`

## 1) Identity
1. Domain: `games`
2. Task group: `cards`
3. Task id: `task_games_cards_hand_count`
4. Objective: answer one integer hand-analysis question from a visible set of face-up playing cards.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_row`
   - `two_row`
2. Supported `query_variant` / emitted `task_variant` values:
   - `same_suit_as_reference_count`
   - `higher_than_reference_count`
   - `pair_count`
   - `longest_run_length`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - all cards are face-up standard playing cards,
   - `single_row` scenes show `7..10` cards in one centered row,
   - `two_row` scenes show `11..14` cards across two centered rows,
   - some variants may mark one card with a visible `REF` banner,
   - `longest_run_length` uses display order; when two rows are shown, the scene includes an explicit continuation cue from the first row to the second.
7. Query contract:
   - `same_suit_as_reference_count` asks how many non-reference cards share the `REF` card's suit,
   - `higher_than_reference_count` asks how many non-reference cards outrank the `REF` card,
   - `pair_count` asks how many ranks appear exactly twice in the hand,
   - `longest_run_length` asks for the length of the unique longest consecutive rank run in display order.
8. Answer policy:
   - `same_suit_as_reference_count`: `0..5`
   - `higher_than_reference_count`: `0..5`
   - `pair_count`: `0..4`
   - `longest_run_length`: `2..6`

## 3) Prompt contract
1. Bundle: `games_cards_v1`
2. `task_family_key`: `visible_card_hand`
3. `task_key`: `cards_hand_query`
4. `task_variant_key`: `same_suit_as_reference_count|higher_than_reference_count|pair_count|longest_run_length`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `rank_order_text` for `higher_than_reference_count`; `rank_order_text`, `continuation_rule_text` for `longest_run_length`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/cards.yaml`,
   - deterministic bundle selection from `prompts/games/cards/games_cards_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Rank wording must state the visible order `2 < ... < 10 < J < Q < K < A` whenever rank comparison or runs are queried.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the relevant cards:
   - all non-reference suit matches for `same_suit_as_reference_count`,
   - all non-reference higher-ranked cards for `higher_than_reference_count`,
   - every card belonging to one of the counted exact pairs for `pair_count`,
   - every card in the unique longest run for `longest_run_length`.
2. `scene_ir.entities` stores one `playing_card` entity per visible card.
3. `render_map` includes:
   - `card_bboxes_px`
   - `reference_card_ids`
   - `row_card_ids`
   - optional `continuation_cue_bbox_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `target_answer`
   - `target_answer_support`
   - `card_count`
   - `card_count_support`
   - `rank_sequence`
   - optional reference-card metadata
   - one visible spec per card (`rank_label`, `rank_value`, `suit_name`, `is_reference`, `order_index`)
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary card chrome/shadow styling only; they do not change card semantics.
3. Card bounding boxes, not the full row area, stay as prompt-facing evidence because every current query is about particular cards.
4. Ordered card-reading tasks must keep row order explicit when the hand wraps to a second row.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, `target_answer`, and `card_count` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible hand.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` or `card_count` outside the feasible support for the chosen query,
   - failure to construct a unique longest run or an exact-pair hand consistent with the requested answer.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_cards_hand_count_contracts.py`
3. Config tests: `tests/test_games_cards_hand_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
