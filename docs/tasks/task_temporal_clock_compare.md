# `task_temporal_clock_compare`

## 1) Identity
1. Domain: `temporal`
2. Task group: `clock`
3. Task id: `task_temporal_clock_compare`
4. Objective: compare several labeled analog clocks and identify the one showing the earliest or latest time.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `earliest_time`
   - `latest_time`
2. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared named-color palette
4. `answer_gt.type`: `string`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - `5..9` labeled analog 12-hour clocks per image,
   - visible labels are sampled from the global pool `A..I`,
   - clocks are arranged in a centered multi-row grid (`3+2`, `3+3`, `3+2+2`, `3+3+2`, or `3+3+3` depending on clock count),
   - no seconds hands,
   - visible hour numerals `1..12`,
   - shown minutes stay on a 5-minute grid in v1,
   - all shown times are distinct,
   - the winning earliest/latest clock is unique by construction,
   - the winning clock differs from the nearest competing clock by at least the configured comparison gap,
   - the visible winner label is sampled from the full label pool before the remaining visible labels are chosen, so answer support stays broad even when the image shows fewer than nine clocks.
7. Query contract:
   - `earliest_time` asks which labeled clock shows the earliest time,
   - `latest_time` asks which labeled clock shows the latest time,
   - prompt-facing answers are always one clock label such as `B`.

## 3) Prompt contract
1. Bundle: `temporal_clock_v1`
2. `task_family_key`: `multi_analog_clock`
3. `task_key`: `clock_compare_query`
4. `task_variant_key`: `earliest_time|latest_time`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/temporal/clock.yaml`,
   - deterministic bundle selection from `prompts/temporal/clock/temporal_clock_v1.json`,
   - variant-conditioned prompt JSON examples generated in task code so the example answer matches the active compare query.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing evidence always names exactly one winning clock-face bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a one-item `bbox_set`:
   - winning clock-face bbox.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - one `clock_face` entity per labeled clock,
   - one `clock_hand` entity for each hour hand,
   - one `clock_hand` entity for each minute hand.
4. `render_map` includes:
   - `scene_bbox_px`
   - `clocks_by_label`
   - `winning_label`
   - `winning_clock_bbox_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - `clock_count`
   - `clock_label_pool`
   - `clock_labels`
   - `shown_total_minutes_by_label`
   - `shown_time_text_by_label`
   - `winner_label`
   - `winner_total_minutes`
   - the active support ranges and minimum comparison-gap threshold

## 5) Visual policy
1. Background and post-image noise use the merged temporal-domain visual defaults from `configs/domains/temporal/base.yaml`.
2. The three `scene_variant` values change only the visible clock chrome.
3. The `style_variant` + `accent_color_name` axes add extra non-semantic color and bezel/tick variety while keeping the prompt unchanged.
4. The face bbox, not the whole row or both hands, is the prompt-facing witness because the answer asks for the winning labeled clock itself.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant`, `scene_variant`, `style_variant`, and `accent_color_name` are sampled independently at the policy level.
3. Answers and evidence come from the same finalized set of shown times.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - empty feasible shown-time support after applying the hand-gap filter,
   - too few feasible later/earlier times to realize the sampled visible clock count under the minimum comparison gap,
   - non-unique visible clock labels.

## 7) Complexity + tests
1. Complexity definition/components: `time_reading`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_clock_compare_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_clock_compare_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
