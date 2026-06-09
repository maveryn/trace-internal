# `task_pages__schedule__maximum_non_overlapping_count`

## Identity
1. Domain: `pages`
2. Scene id: `schedule`
3. Source task group: `schedule`
4. Task id: `task_pages__schedule__maximum_non_overlapping_count`

## Contract
1. Objective: find the maximum number of mutually non-overlapping scheduled events.
2. Branch metadata: `query_id`
3. `query_id`: `maximum_non_overlapping_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over the unique maximum-cardinality non-overlapping event set.

## Prompt + Trace
1. Prompt bundle: `pages_schedule_v0`
2. Scene key: `day_schedule`
3. Task key: `schedule_day_query`
4. Internal prompt variant key: `maximum_non_overlapping_count`
5. Trace records event intervals, lane assignments, answer event ids, and event bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized schedule metadata.
