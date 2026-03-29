# `task_temporal_clock_readout`

## 1) Identity
1. Domain: `temporal`
2. Task group: `clock`
3. Task id: `task_temporal_clock_readout`
4. Objective: read the shown time from one analog clock or apply one minute offset to that shown time.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `shown_time`
   - `minutes_after`
   - `minutes_before`
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
   - one analog 12-hour clock per image,
   - hour numerals `1..12` are always visible,
   - there is no seconds hand,
   - shown minutes stay on a 5-minute grid in v1,
   - shown times whose hour/minute hands are too close are filtered out by the configured minimum hand-angle-gap threshold.
7. Query contract:
   - `shown_time` asks for the displayed time itself,
   - `minutes_after` asks for the time a sampled number of minutes after the displayed time,
   - `minutes_before` asks for the time a sampled number of minutes before the displayed time,
   - prompt-facing answers always use strict `HH:MM` 12-hour formatting with leading zeros.
8. Offset policy:
   - offset minutes come from the configured support (default `5..55` in 5-minute increments),
   - the displayed clock does not change between variants; only the query changes.

## 3) Prompt contract
1. Bundle: `temporal_clock_v1`
2. `task_family_key`: `single_analog_clock`
3. `task_key`: `clock_readout_query`
4. `task_variant_key`: `shown_time|minutes_after|minutes_before`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `delta_minutes` for `minutes_after|minutes_before`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/temporal/clock.yaml`,
   - deterministic bundle selection from `prompts/temporal/clock/temporal_clock_v1.json`,
   - variant-conditioned prompt JSON examples generated in task code so offset examples always match the active `delta_minutes`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing evidence always names exactly two hand bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly two `bbox_set` items:
   - hour-hand bbox,
   - minute-hand bbox.
2. `projected_evidence` includes:
   - `bbox_set`
   - `pixel_point_map` with `clock_center`, `hour_hand_tip`, and `minute_hand_tip`
3. `scene_ir.entities` stores:
   - one `clock_face` entity,
   - one `clock_hand` entity for the hour hand,
   - one `clock_hand` entity for the minute hand.
4. `render_map` includes:
   - `scene_bbox_px`
   - `face_bbox_px`
   - `center_px`
   - `hand_bboxes_px`
   - `hand_tips_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - shown time as total minutes plus `shown_hour|shown_minute|shown_time_text`
   - `delta_minutes` when present
   - `answer_time_text`
   - support ranges for hour/minute/delta sampling
   - the active minimum hand-angle-gap threshold

## 5) Visual policy
1. Background and post-image noise use the merged temporal-domain visual defaults from `configs/domains/temporal/base.yaml`.
2. The three `scene_variant` values change the visible clock chrome only; they do not change the time semantics.
3. The independent `style_variant` + `accent_color_name` axes add extra non-semantic color and bezel/tick variety while keeping the prompt unchanged.
4. The minute hand remains visually distinct from the hour hand by color and width under every supported theme.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same finalized shown time and hand geometry.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - empty feasible shown-time support after applying the minute grid and hand-gap filter,
   - explicit shown time outside configured support,
   - explicit offset outside configured support.

## 7) Complexity + tests
1. Complexity definition/components: `time_reading`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_clock_readout_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_clock_readout_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
