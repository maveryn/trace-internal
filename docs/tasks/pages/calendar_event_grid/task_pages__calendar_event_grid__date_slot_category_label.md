# `task_pages__calendar_event_grid__date_slot_category_label`

## Identity
1. Domain: `pages`
2. Scene id: `calendar_event_grid`
3. Source scene package: `calendar_event_grid`
4. Task id: `task_pages__calendar_event_grid__date_slot_category_label`

## Contract
1. Objective: read the visible category label in a requested event slot on a requested calendar date.
2. Branch metadata: `query_id`
3. `query_id`: `date_slot_category_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `date_cell` and `event_chip` boxes.
6. Query knobs: date number and event slot label.

## Prompt + Trace
1. Prompt bundle: `pages_calendar_event_grid_v0`
2. Scene key: `calendar_event_grid`
3. Task key: `calendar_event_grid_query`
4. Internal prompt variant key: `date_slot_category_label`
5. Trace records the month/year, slot/category chips, final date-cell bboxes, and final event-chip bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized calendar event-grid metadata.
