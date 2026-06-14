# `task_pages__calendar__weekday_occurrence_date`

## Identity
1. Domain: `pages`
2. Scene id: `calendar`
3. Source scene: `calendar`
4. Task id: `task_pages__calendar__weekday_occurrence_date`

## Contract
1. Objective: find the date number of an nth weekday in one Gregorian month-view calendar.
2. Branch metadata: `query_id`
3. `query_id`: `date_of_weekday_occurrence`
4. Answer type: `integer`
5. Annotation type: `bbox_set` containing the target date-cell bbox.
6. Query knobs: weekday name and occurrence ordinal.

## Prompt + Trace
1. Prompt bundle: `pages_calendar_v0`
2. Scene key: `month_calendar`
3. Task key: `calendar_month_query`
4. Internal prompt variant key: `date_of_weekday_occurrence`
5. Trace records the month/year, weekday/ordinal query, answer date, and date-cell bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized calendar metadata.
