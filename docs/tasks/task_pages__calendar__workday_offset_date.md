# `task_pages__calendar__workday_offset_date`

## Identity
1. Domain: `pages`
2. Scene id: `calendar`
3. Source task group: `calendar`
4. Task id: `task_pages__calendar__workday_offset_date`

## Contract
1. Objective: find the date number reached by moving a requested number of workdays before or after one marked reference date, skipping Saturdays and Sundays.
2. Branch metadata: `query_id`
3. `query_id`: `workday_after_offset_date` or `workday_before_offset_date`
4. Answer type: `integer`
5. Annotation type: `keyed_bbox_map` over the reference and target date cells, keyed as `reference_date` and `target_date`.
6. Query knobs: workday direction and offset count.

## Prompt + Trace
1. Prompt bundle: `pages_calendar_v0`
2. Scene key: `month_calendar`
3. Task key: `calendar_month_query`
4. Internal prompt variant keys: `workday_after_offset_date` and `workday_before_offset_date`
5. Trace records the month/year, reference date, target date, direction, offset, weekend indices, and date-cell bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized calendar metadata.
