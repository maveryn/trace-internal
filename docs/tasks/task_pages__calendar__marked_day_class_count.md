# `task_pages__calendar__marked_day_class_count`

## Identity
1. Domain: `pages`
2. Scene id: `calendar`
3. Source task group: `calendar`
4. Task id: `task_pages__calendar__marked_day_class_count`

## Contract
1. Objective: count how many marked dates in one month-view calendar fall on the requested day class.
2. Public `query_variant`: `default`
3. `query_id`: `count_marked_weekend_days` or `count_marked_weekday_days`
4. Answer type: `integer`
5. Evidence type: `bbox_set` over the marked date cells that satisfy the query.
6. Mirror/query knob: `marked_day_class=weekend|weekday`

## Prompt + Trace
1. Prompt bundle: `pages_calendar_v0`
2. Scene key: `month_calendar`
3. Task key: `calendar_month_query`
4. Internal prompt variant key: `count_marked_day_class`
5. Trace records the month/year, marked dates, evidence dates, day-class query, and date-cell bboxes.
6. Generation is deterministic from `instance_seed`; answers and evidence come from the finalized calendar metadata.
