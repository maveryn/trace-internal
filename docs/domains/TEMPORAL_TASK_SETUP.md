# Temporal Task Setup

## Purpose
Capture the active v1 contract for the `temporal` domain.

This is the active temporal-domain contract. For cross-domain coverage rollups,
use `docs/project/STATUS.md` and `docs/domains/TASK_FAMILY_VARIANTS.md` instead
of repeating those inventories in temporal-specific notes or skills.

## Active families
1. Current active `task_group` values:
   - `clock`
   - `calendar`
   - `schedule`
   - `timeline`
2. Current active tasks:
   - `task_temporal_clock_readout`
   - `task_temporal_clock_compare`
   - `task_temporal_calendar_month_view`
   - `task_temporal_schedule_day_planner`
   - `task_temporal_timeline_milestones`

## Family contract
1. Temporal tasks use familiar time-structured visual artifacts rather than generic tables or charts.
2. Early temporal tasks should prefer displays with one visually obvious queried object so prompt-facing evidence can stay local and reviewable.
3. The active clock family now covers both one-clock readout and multi-clock comparison while keeping one stable analog-clock grammar shared across the task group.
4. The active calendar family now uses one stable month-view scaffold and widens question diversity through `task_variant` rather than changing the calendar scene grammar itself.
5. The active schedule family now uses one stable single-day planner scaffold and widens question diversity through `task_variant` rather than forking separate schedule task ids for overlap, duration, and optimization questions.
6. The active timeline family now uses one stable milestone-roadmap scaffold and widens question diversity through `task_variant` rather than forking separate task ids for before/between/position timeline queries.

## `task_temporal_clock_readout`
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
   - `accent_color_name`: shared named-color palette
4. Answer contract:
   - `answer_gt.type = string`
   - prompt-facing answer format is strict `HH:MM` in 12-hour time with leading zeros
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly two hand bboxes: hour hand + minute hand
6. Scene contract:
   - one analog 12-hour clock per image,
   - no seconds hand,
   - visible hour numerals `1..12`,
   - shown minutes stay on a 5-minute grid in v1,
   - shown times with nearly overlapping hour/minute hands are filtered out by a minimum hand-angle-gap rule,
   - `minutes_after` and `minutes_before` use minute offsets sampled from the configured support and keep the displayed clock itself unchanged.
7. Trace contract:
   - `scene_ir.entities` includes the clock face plus one entity per hand,
   - `render_map.hand_bboxes_px` stores both hand bboxes keyed by hand kind,
   - `render_map.hand_tips_px` stores both hand tips in pixel space,
   - `execution_trace` records the shown time, offset minutes when present, answer time text, the active support ranges, and the sampled `style_variant` + `accent_color_name`,
   - prompt-facing evidence is projected from the recorded hand geometry, not inferred from pixels.

## Prompt contract
1. Bundles:
   - `temporal_clock_v1`
   - `temporal_calendar_v1`
   - `temporal_schedule_v1`
   - `temporal_timeline_v1`
2. `task_temporal_clock_readout` uses `task_family_key=single_analog_clock` and `task_key=clock_readout_query`.
3. `task_temporal_clock_compare` uses `task_family_key=multi_analog_clock` and `task_key=clock_compare_query`.
4. `task_temporal_calendar_month_view` uses `task_family_key=month_calendar` and `task_key=calendar_month_query`.
5. `task_temporal_schedule_day_planner` uses `task_family_key=day_schedule` and `task_key=schedule_day_query`.
6. `task_temporal_timeline_milestones` uses `task_family_key=milestone_timeline` and `task_key=timeline_milestone_query`.
7. `task_variant_key` values stay task-specific:
   - `shown_time|minutes_after|minutes_before` for readout
   - `earliest_time|latest_time` for compare
   - `date_of_weekday_occurrence|count_marked_weekend_days|days_between_marked_dates` for calendar
   - `overlap_count|longer_than_reference_count|maximum_non_overlapping_count` for schedule
   - `before_reference_count|between_reference_events_count|position_of_reference` for timeline
8. Required slots:
   - task-family: `object_description`
   - task-variant: `delta_minutes` for the readout offset variants only
   - task-variant: `ordinal`, `weekday_name` for `date_of_weekday_occurrence`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
9. Prompt-facing examples must match the active query semantics; for readout offset variants, do not reuse the shown-time example answer unchanged.

## Visual policy
1. Temporal tasks use the same light solid background baseline as the other clean synthetic domains.
2. `classic`, `minimal`, and `outline` vary artifact chrome only; they do not change the underlying time semantics.
3. `style_variant` and `accent_color_name` add extra non-semantic temporal diversity while keeping the same answer/evidence contract.
4. The queried witness should stay visually separable in every active family, which is why clocks filter near-overlap hand placements, calendars keep evidence on date cells, schedules keep evidence on event blocks, and timelines keep evidence on event cards instead of the full axis.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: the answer always comes from the same finalized artifact metadata recorded in trace.
4. Review/sample overlays should use recorded witness geometry (for example hand bboxes/tips, date-cell bboxes, or event-block bboxes) rather than guessing geometry from pixels.

## `task_temporal_clock_compare`
1. Supported `task_variant` values:
   - `earliest_time`
   - `latest_time`
2. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: shared named-color palette
4. Answer contract:
   - `answer_gt.type = string`
   - prompt-facing answer is one visible clock label such as `A` or `F`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one winning clock-face bbox
6. Scene contract:
   - `5..9` labeled analog clocks in a centered multi-row grid,
   - visible labels are sampled from the global pool `A..I`,
   - no seconds hands,
   - visible hour numerals `1..12`,
   - shown minutes stay on a 5-minute grid in v1,
   - the earliest/latest winner is unique by construction and separated from the nearest competitor by a minimum comparison gap,
   - the winner label is sampled from the full label pool before the remaining visible labels are chosen so the answer support stays broad across `5..9` visible clocks.
7. Trace contract:
   - `render_map.clocks_by_label` stores one face bbox plus both hand bboxes/tips for every visible clock,
   - `render_map.winning_clock_bbox_px` stores the prompt-facing witness,
   - `execution_trace` records `clock_count`, the full label pool, the shown time for every visible label, and the unique winning label.

## `task_temporal_calendar_month_view`
1. Supported `task_variant` values:
   - `date_of_weekday_occurrence`
   - `count_marked_weekend_days`
   - `days_between_marked_dates`
2. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
3. Supported non-semantic visual axes:
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: shared named-color palette
4. Answer contract:
   - `answer_gt.type = integer`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one or more date-cell bboxes, depending on the active variant
6. Scene contract:
   - one real Gregorian month-view calendar per image,
   - weekday headers are Monday-first,
   - the month may occupy `4`, `5`, or `6` visible week rows,
   - marked dates appear only for the marked-date variants,
   - prompt-facing evidence always stays on date cells rather than header rows or title regions.
7. Trace contract:
   - `render_map.date_cells_by_day` stores the pixel bbox for every valid day in the month,
   - `render_map.marked_dates` stores the marked date numbers when present,
   - `execution_trace` records the month/year metadata, the sampled row count, the marked/evidence dates, and any query-specific fields such as nth-weekday metadata or the targeted day gap.

## `task_temporal_schedule_day_planner`
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
   - `accent_color_name`: shared named-color palette
4. Answer contract:
   - `answer_gt.type = integer`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one or more event-block bboxes depending on the active variant
6. Scene contract:
   - one single-day planner per image,
   - one vertical time axis with scheduled event blocks rendered in overlapping lanes when necessary,
   - a highlighted reference event for the first two variants only,
   - the optimization variant uses the same planner scaffold without a reference event,
   - prompt-facing evidence stays on event blocks rather than widening to empty schedule regions or header chrome.
7. Query contract:
   - `overlap_count` asks how many other scheduled events overlap the highlighted reference event,
   - `longer_than_reference_count` asks how many other scheduled events are longer than the highlighted reference event,
   - `maximum_non_overlapping_count` asks for the size of the unique maximum-cardinality non-overlapping event subset.
8. Trace contract:
   - `render_map.event_bboxes_by_id` stores one bbox per event block,
   - `render_map.answer_event_ids` stores the witness event ids,
   - `execution_trace.events` records the start/end slot, start/end time text, lane index, duration, and reference flag for every event,
   - `execution_trace.answer_event_ids` records the exact event subset used for answer/evidence.

## `task_temporal_timeline_milestones`
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
   - `accent_color_name`: shared named-color palette
4. Answer contract:
   - `answer_gt.type = integer`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one or more event-card bboxes depending on the active variant
6. Scene contract:
   - one horizontal milestone timeline per image,
   - one dated event card per visible event,
   - one highlighted reference event for `before_reference_count` and `position_of_reference`,
   - two highlighted reference events for `between_reference_events_count`,
   - prompt-facing evidence stays on event cards rather than the full axis.
7. Trace contract:
   - `render_map.event_bboxes_by_id` stores one bbox per event card,
   - `render_map.answer_event_ids` stores the witness event ids,
   - `execution_trace.events` records order index, day-of-month, date label, card side, and reference kind for every event,
   - `execution_trace.reference_event_ids` records the highlighted reference event ids.
