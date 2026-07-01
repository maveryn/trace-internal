# `task_pages__calendar_event_grid__date_slot_category_label`

## Identity
1. Domain: `pages`
2. Scene id: `calendar_event_grid`
3. Source scene: `calendar_event_grid`
4. Task id: `task_pages__calendar_event_grid__date_slot_category_label`

## Contract
1. Objective: read the visible category label in a requested event slot on a requested calendar date.
2. Public task contract: `date_slot_category_label`
3. Supported `query_id` values: `single`
4. Answer type: `string`
5. Annotation schema: `bbox`
6. Annotation witness: the requested event-chip box.
7. Query argument axes: sampled date number and event slot label.

## Program Contract
- `calendar_event_grid_date_slot_category_lookup(date_number, slot_id); output=category_label_string; annotation=bbox(requested_event_chip); scene=calendar_event_grid; scope=one month calendar with Top/Mid/End event slots`

## Prompt + Trace
1. Prompt bundle: `pages_calendar_event_grid_v1`
2. Scene key: `calendar_event_grid`
3. Task key: `calendar_event_grid_query`
4. Prompt query key: `date_slot_category_label`
5. Trace records the month/year, target date, slot/category chips, final date-cell bboxes, and final event-chip bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized calendar event-grid metadata.
