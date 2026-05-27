# `task_pages__schedule__overlap_count`

## Identity
1. Domain: `pages`
2. Scene id: `schedule`
3. Source task group: `schedule`
4. Task id: `task_pages__schedule__overlap_count`

## Contract
1. Objective: count scheduled events that overlap the highlighted reference event.
2. Branch metadata: `query_id`
3. `query_id`: `overlap_count`
4. Answer type: `integer`
5. Evidence type: `bbox_set` over all event blocks that overlap the reference event.

## Prompt + Trace
1. Prompt bundle: `pages_schedule_v0`
2. Scene key: `day_schedule`
3. Task key: `schedule_day_query`
4. Internal prompt variant key: `overlap_count`
5. Trace records event intervals, lane assignments, reference event id, answer event ids, reference guide rendering, and event bboxes.
6. Generation is deterministic from `instance_seed`; answers and evidence come from the finalized schedule metadata.
