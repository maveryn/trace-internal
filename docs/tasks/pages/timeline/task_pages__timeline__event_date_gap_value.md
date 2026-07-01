# `task_pages__timeline__event_date_gap_value`

## Identity
1. Domain: `pages`
2. Scene id: `timeline`
3. Source scene: `timeline`
4. Task id: `task_pages__timeline__event_date_gap_value`

## Program Contract
1. Program schema: `timeline_event_date_gap_value(endpoint_event_pair) -> calendar_day_gap; scene=timeline; scope=event_date_gap_value`
2. Scene: `timeline`
3. Scope: one rendered milestone timeline with dated event cards and two highlighted endpoint events.
4. Supported `query_id`: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_map`
7. Annotation roles: `earlier_event`, `later_event`.
8. Query arguments: endpoint prompt order varies, but the reasoning program remains the same calendar-day difference.
9. Render arguments: month/year, event count, scene variant, style variant, accent color, render dimensions, and post-render noise.

## Prompt + Trace
1. Prompt bundle: `pages_timeline_v1`
2. Scene key: `milestone_timeline`
3. Task key: `timeline_milestone_query`
4. Prompt query key: `event_date_gap_value`
5. Trace records `query_id=single`, `source_query_id=event_date_gap_value`, endpoint event ids, prompt endpoint order, event dates, endpoint event-card bboxes, style metadata, and role-keyed projected annotation.
6. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.
