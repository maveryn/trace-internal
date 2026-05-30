# `task_pages__schedule__reference_interval_count`

## Identity
1. Domain: `pages`
2. Scene id: `schedule`
3. Source task group: `schedule`
4. Task id: `task_pages__schedule__reference_interval_count`

## Contract
Counts scheduled event blocks satisfying a relation to the highlighted reference event.

Query ids: `overlap_count|longer_than_reference_count`.

Answers are integers. Evidence is a `bbox_set` over all event blocks satisfying the requested relation.

## Prompt + Trace
1. Prompt bundle: `pages_schedule_v0`
2. Scene key: `day_schedule`
3. Task key: `schedule_day_query`
4. Trace records event intervals, durations, lane assignments, reference event id, answer event ids, and event bboxes.
5. Generation is deterministic from `instance_seed`; answers and evidence come from finalized schedule metadata.
