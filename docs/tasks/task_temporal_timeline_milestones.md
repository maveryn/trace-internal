# `task_temporal_timeline_milestones`

## 1) Identity
1. Domain: `temporal`
2. Task group: `timeline`
3. Task id: `task_temporal_timeline_milestones`
4. Objective: answer numeric ordering questions from one milestone-style horizontal timeline.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `before_reference_count`
   - `between_reference_events_count`
   - `position_of_reference`
2. Supported `scene_variant` values:
   - `classic`
   - `roadmap`
   - `minimal`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared named-color palette
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - one horizontal milestone timeline per image,
   - one dated event card per visible milestone,
   - event cards are arranged from earliest to latest along the axis,
   - one highlighted reference event appears for `before_reference_count` and `position_of_reference`,
   - two highlighted reference events appear for `between_reference_events_count`,
   - prompt-facing evidence always stays on event cards rather than expanding to the full timeline axis.
7. Query contract:
   - `before_reference_count` asks how many events happen before the highlighted reference event,
   - `between_reference_events_count` asks how many events happen strictly between the two highlighted reference events,
   - `position_of_reference` asks for the highlighted reference event's 1-based position from earliest to latest.

## 3) Prompt contract
1. Bundle: `temporal_timeline_v1`
2. `task_family_key`: `milestone_timeline`
3. `task_key`: `timeline_milestone_query`
4. `task_variant_key`: `before_reference_count|between_reference_events_count|position_of_reference`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/temporal/timeline.yaml`,
   - deterministic bundle selection from `prompts/temporal/timeline/temporal_timeline_v1.json`,
   - variant-conditioned prompt JSON examples generated in task code so the example answer/evidence shape matches the active query.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is always one integer, while prompt-facing evidence always names one or more event-card bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` over event cards:
   - all event cards before the reference event for `before_reference_count`,
   - all event cards strictly between the two reference events for `between_reference_events_count`,
   - every event card from the earliest event through the highlighted reference event, including the reference event itself, for `position_of_reference`.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - one `timeline_event_card` entity per visible event.
4. `render_map` includes:
   - `scene_bbox_px`
   - `panel_bbox_px`
   - `axis_bbox_px`
   - `title_text`
   - `subtitle_text`
   - `event_bboxes_by_id`
   - `answer_event_ids`
   - `reference_event_ids`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `style_variant`
   - `accent_color_name`
   - `year`
   - `month`
   - `month_name`
   - `event_count`
   - `answer_value`
   - `answer_event_ids`
   - `reference_event_ids`
   - the full event list with per-event order index, day-of-month, date label, card side, and reference kind

## 5) Visual policy
1. Background and post-image noise use the merged temporal-domain visual defaults from `configs/domains/temporal/base.yaml`.
2. `classic`, `roadmap`, and `minimal` vary timeline chrome only; they do not change event ordering semantics.
3. `style_variant` + `accent_color_name` add non-semantic milestone-timeline diversity through panel, axis, marker, and event-card styling while keeping the same answer/evidence contract.
4. Event-card bboxes, not the entire axis or long connector lines, stay as the prompt-facing witness for all current variants.

## 6) Determinism + constraints
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant`, `scene_variant`, `style_variant`, and `accent_color_name` are sampled independently at the policy level.
3. Answers and evidence come from the same finalized event ordering and event-card geometry.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported year/month bounds,
   - empty feasible support for the active variant under the configured event-count or answer support,
   - months that cannot host the requested number of unique dated events,
   - missing highlighted reference events after final event construction.

## 7) Complexity + tests
1. Complexity definition/components: `temporal_order_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_temporal_timeline_milestones_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_temporal_timeline_milestones_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
