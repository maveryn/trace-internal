# `task_pages__calendar_event_grid__category_slot_day_count`

## Identity
1. Domain: `pages`
2. Scene id: `calendar_event_grid`
3. Source scene package: `calendar_event_grid`
4. Task id: `task_pages__calendar_event_grid__category_slot_day_count`

## Contract
1. Objective: count dates whose requested event slot contains the requested category label.
2. Branch metadata: `query_id`
3. `query_id`: `category_slot_day_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over matching event-chip boxes.
6. Query knobs: category label and event slot label.

## Prompt + Trace
1. Prompt bundle: `pages_calendar_event_grid_v0`
2. Scene key: `calendar_event_grid`
3. Task key: `calendar_event_grid_query`
4. Internal prompt variant key: `category_slot_day_count`
5. Trace records the month/year, slot/category chips, matching chip ids, final date-cell bboxes, and final event-chip bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized calendar event-grid metadata.
