# `task_pages__timeline__event_date_gap_value`

## Identity
1. Domain: `pages`
2. Scene id: `timeline`
3. Source scene: `timeline`
4. Task id: `task_pages__timeline__event_date_gap_value`

## Contract
1. Objective: compute the nonnegative calendar-day gap between two named milestone events on one timeline.
2. Branch metadata: `query_id`
3. `query_id`: `event_date_gap_value`
4. Answer type: `integer`
5. Annotation type: `keyed_bbox_map` over the two endpoint event cards, keyed as `earlier_event` and `later_event`.
6. Query variation: endpoint prompt order and sampled day-gap value vary within the same date-arithmetic program contract.

## Prompt + Trace
1. Prompt bundle: `pages_timeline_v0`
2. Scene key: `milestone_timeline`
3. Task key: `timeline_milestone_query`
4. Internal prompt variant key: `event_date_gap_value`
5. Trace records event order, dates, endpoint event ids, prompt endpoint order, answer day gap, and event-card bboxes.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized timeline metadata.
