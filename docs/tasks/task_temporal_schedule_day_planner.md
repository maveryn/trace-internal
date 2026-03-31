# `task_temporal_schedule_day_planner`

## 1) Identity
1. Domain: `temporal`
2. Task group: `schedule`
3. Task id: `task_temporal_schedule_day_planner`
4. Objective: answer numeric schedule questions from one single-day planner view.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `overlap_count`
   - `longer_than_reference_count`
   - `maximum_non_overlapping_count`
2. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared named-color palette
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - one single-day planner per image,
   - one vertical time axis spanning the configured day window,
   - scheduled events render as visible event blocks with short non-semantic labels,
   - overlaps are rendered by lane assignment inside the same planner,
   - a highlighted reference event appears only for the reference-based variants,
   - prompt-facing evidence always stays on event blocks rather than widening to headers, time labels, or empty background.
7. Query contract:
   - `overlap_count` asks how many other scheduled events overlap the highlighted reference event,
   - `longer_than_reference_count` asks how many other scheduled events are longer than the highlighted reference event,
   - `maximum_non_overlapping_count` asks for the size of the unique maximum-cardinality non-overlapping event subset.

## 3) Prompt contract
1. Bundle: `temporal_schedule_v1`
2. `task_family_key`: `day_schedule`
3. `task_key`: `schedule_day_query`
4. `task_variant_key`: `overlap_count|longer_than_reference_count|maximum_non_overlapping_count`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/temporal/schedule.yaml`,
   - deterministic bundle selection from `prompts/temporal/schedule/temporal_schedule_v1.json`,
   - variant-conditioned prompt JSON examples generated in task code so the example answer/evidence shape matches the active schedule question.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is always one integer, while prompt-facing evidence always names one or more event-block bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` over event blocks:
   - all overlapping event blocks for `overlap_count`,
   - all longer-than-reference event blocks for `longer_than_reference_count`,
   - the unique maximum-size non-overlapping event set for `maximum_non_overlapping_count`.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - one `scheduled_event_block` entity per visible event.
4. `render_map` includes:
   - `scene_bbox_px`
   - `panel_bbox_px`
   - `title_text`
   - `day_label`
   - `event_bboxes_by_id`
   - `answer_event_ids`
   - `reference_event_id`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - `day_label`
   - `start_hour`
   - `end_hour`
   - `slot_minutes`
   - `event_count`
   - `lane_count`
   - `answer_value`
   - `answer_event_ids`
   - the full event list with per-event start/end slot, start/end time text, lane index, duration, and reference flag

## 5) Visual policy
1. Background and post-image noise use the merged temporal-domain visual defaults from `configs/domains/temporal/base.yaml`.
2. `classic`, `minimal`, and `outline` vary planner chrome and grid density only; they do not change schedule semantics.
3. `style_variant` + `accent_color_name` add non-semantic day-planner diversity through header, grid, and event-block styling while keeping the same answer/evidence contract.
4. Event-block bboxes, not empty gaps or wide planner regions, stay as the prompt-facing witness for all current variants.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant`, `scene_variant`, `style_variant`, and `accent_color_name` are sampled independently at the policy level.
3. Answers and evidence come from the same finalized event intervals and event-block geometry.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - sampled schedules that exceed the configured planner lane cap,
   - empty feasible support for the active variant under the configured event-count or duration support,
   - reference-based scenes that cannot realize the requested overlap-count or longer-than count,
   - optimization scenes that fail the unique-optimum non-overlapping-set construction.

## 7) Complexity + tests
1. Complexity definition/components: `interval_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_schedule_day_planner_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_schedule_day_planner_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
