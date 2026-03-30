# `task_games_dominoes_chain_count`

## 1) Identity
1. Domain: `games`
2. Task group: `dominoes`
3. Task id: `task_games_dominoes_chain_count`
4. Objective: answer one integer counting question from a visible domino scene with a short top chain and loose face-up dominoes below.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_row`
   - `two_row`
2. Supported `query_variant` / emitted `task_variant` values:
   - `matching_end_count`
   - `higher_sum_than_reference_count`
   - `sum_to_target_count`
   - `double_count`
3. Supported non-semantic visual axis:
   - `style_variant`: `classic|soft|outlined`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the top row always shows one valid left-to-right domino chain,
   - loose face-up candidate dominoes always appear below the chain,
   - `single_row` scenes show `7..9` loose candidates in one centered row,
   - `two_row` scenes show `10..12` loose candidates across two centered rows,
   - `matching_end_count` and `higher_sum_than_reference_count` mark the rightmost chain tile with `REF`,
   - `matching_end_count` also outlines the open right half of that `REF` tile.
7. Query contract:
   - `matching_end_count` asks how many loose dominoes below could connect to the open right end of the `REF` tile,
   - `higher_sum_than_reference_count` asks how many loose dominoes below have a larger pip sum than the `REF` tile,
   - `sum_to_target_count` asks how many loose dominoes below have pip sum equal to a shown target total,
   - `double_count` asks how many loose dominoes below are doubles.
8. Answer policy:
   - `matching_end_count`: `0..5`
   - `higher_sum_than_reference_count`: `0..5`
   - `sum_to_target_count`: `0..4`
   - `double_count`: `0..5`

## 3) Prompt contract
1. Bundle: `games_dominoes_v1`
2. `task_family_key`: `visible_domino_chain`
3. `task_key`: `domino_chain_query`
4. `task_variant_key`: `matching_end_count|higher_sum_than_reference_count|sum_to_target_count|double_count`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `matching_end_count`: `connection_rule_text`
     - `higher_sum_than_reference_count`: `pip_sum_rule_text`
     - `sum_to_target_count`: `pip_sum_rule_text`, `target_total_text`
     - `double_count`: `double_rule_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/games/dominoes.yaml`,
   - deterministic bundle selection from `prompts/games/dominoes/games_dominoes_v1.json`,
   - task-local JSON examples generated from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt policy:
   - count only the loose dominoes below the chain,
   - explain connection / pip-sum / double semantics explicitly in the prompt whenever the query depends on them.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over the matching loose dominoes below the chain:
   - every loose domino that can connect to the open right end for `matching_end_count`,
   - every loose domino whose pip sum is larger than `REF` for `higher_sum_than_reference_count`,
   - every loose domino whose pip sum equals the target total for `sum_to_target_count`,
   - every loose domino below that is a double for `double_count`.
2. `scene_ir.entities` stores one `domino_tile` entity per visible tile.
3. `render_map` includes:
   - `domino_bboxes_px`
   - `chain_tile_ids`
   - `candidate_tile_ids`
   - `candidate_row_ids`
   - optional `reference_tag_bboxes_px`
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `task_variant`
   - `style_variant`
   - `target_answer`
   - `target_answer_support`
   - `candidate_count`
   - `candidate_count_support`
   - optional `reference_tile_id`
   - optional `open_end_value`
   - optional `reference_sum`
   - optional `target_total`
   - chain and candidate tile specs with visible half values and roles
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged games-domain visual defaults from `configs/domains/games/base.yaml`.
2. `classic`, `soft`, and `outlined` vary domino chrome/shadow styling only; they do not change tile semantics.
3. Prompt-facing evidence stays on the loose candidate tiles below the chain, not on the top chain itself, because the chain is reference/context rather than the counted witness set.
4. Keep the `REF` tag and open-end highlight visually strong enough that the operative chain tile is obvious without widening the evidence.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `style_variant`, `target_answer`, and `candidate_count` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized visible domino scene.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer`, `candidate_count`, or `target_total` outside the feasible support for the chosen query,
   - failure to construct a valid top chain consistent with the query-specific witness pool.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `card_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_games_dominoes_chain_count_contracts.py`
3. Config tests: `tests/test_games_dominoes_chain_count_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
