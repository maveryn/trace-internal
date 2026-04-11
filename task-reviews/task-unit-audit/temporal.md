# Temporal Task-Unit Audit

Task-unit audit for `domain=temporal` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The temporal domain is in good shape as a benchmark-unit inventory.
2. Each task keeps one very stable temporal visual grammar—clock, calendar, planner, or timeline—while still supporting enough within-task variation.
3. Some tasks mix reference-based and non-reference-based queries, but the underlying perceptual job remains coherent enough that no split feels necessary right now.
4. Recommended domain outcome:
   - `Keep`: `5`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_temporal_calendar_month_view`
- Outcome: `Keep`
- Why: one coherent month-calendar family over a stable single-month grid scaffold.
- Scene variety: moderate; month/year choice, row count, style, and marked-date placement vary while the calendar grammar stays fixed.
- Query variety: moderate (`date_of_weekday_occurrence|count_marked_weekend_days|days_between_marked_dates`) but still one stable date-cell reasoning family.
- Grounding necessity: strong; the solver must inspect the actual month layout and relevant date cells.
- Evidence fit: good; relevant date-cell bboxes are the natural witness across all variants.
- Follow-up: none required now.

### `task_temporal_clock_compare`
- Outcome: `Keep`
- Why: one coherent multi-clock comparison family.
- Scene variety: moderate; clock count, shown times, labels, and styling vary while the multi-clock grid stays stable.
- Query variety: modest but coherent (`earliest_time|latest_time`).
- Grounding necessity: strong; the solver must read several analog clocks and compare them.
- Evidence fit: good; the winning clock-face bbox is the natural witness.
- Follow-up: none required now.

### `task_temporal_clock_readout`
- Outcome: `Keep`
- Why: one coherent single-clock readout / offset family.
- Scene variety: moderate; displayed time and styling vary while the single-clock scaffold stays stable.
- Query variety: moderate (`shown_time|minutes_after|minutes_before`) but still one stable clock-readout family.
- Grounding necessity: strong; the solver must read the shown hands before optionally applying the offset.
- Evidence fit: good; the hour-hand and minute-hand bboxes are the natural witness.
- Follow-up: none required now.

### `task_temporal_schedule_day_planner`
- Outcome: `Keep`
- Why: one coherent day-planner event reasoning family.
- Scene variety: moderate; event count, lane arrangement, and styling vary within one stable planner grammar.
- Query variety: moderate (`overlap_count|longer_than_reference_count|maximum_non_overlapping_count`) but still one event-block family over the same schedule scaffold.
- Grounding necessity: strong; the model must inspect event extents and overlaps in the planner itself.
- Evidence fit: acceptable; reference-based variants and maximum-subset variants use slightly different witness sets, but all evidence stays on event blocks and the interaction grammar is still coherent.
- Follow-up: if the schedule family expands later, `maximum_non_overlapping_count` is the first variant to revisit for a possible split.

### `task_temporal_timeline_milestones`
- Outcome: `Keep`
- Why: one coherent milestone-ordering family over a stable horizontal timeline.
- Scene variety: moderate; event count, highlighted references, and styling vary while the timeline grammar stays fixed.
- Query variety: moderate (`before_reference_count|between_reference_events_count|position_of_reference`) but still one stable event-ordering family.
- Grounding necessity: strong; the solver must reason from the visible order of event cards on the timeline.
- Evidence fit: good; relevant event-card bboxes are the natural witness across all variants.
- Follow-up: none required now.

## Recommended next action
1. Leave the temporal domain unchanged for now.
2. Keep an eye on `task_temporal_schedule_day_planner` only if its optimization-style schedule variants expand substantially later.
