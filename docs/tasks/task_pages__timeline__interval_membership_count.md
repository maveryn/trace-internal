# `task_pages__timeline__interval_membership_count`

## Identity
1. Domain: `pages`
2. Scene id: `timeline`
3. Source task group: `timeline`
4. Task id: `task_pages__timeline__interval_membership_count`

## Contract
1. Objective: count timeline events inside or outside the interval defined by two highlighted reference events.
2. Public `query_variant`: `default`
3. `query_id`: `between_reference_events_count` or `outside_reference_interval_count`
4. Answer type: `integer`
5. Evidence type: `bbox_set` over the event cards that satisfy the interval relation.
6. Mirror/query knob: `interval_relation=between|outside`

## Prompt + Trace
1. Prompt bundle: `pages_timeline_v0`
2. Scene key: `milestone_timeline`
3. Task key: `timeline_milestone_query`
4. Internal prompt variant key: `interval_membership_count`
5. Trace records event order, dates, reference event ids, answer event ids, and event-card bboxes.
6. Generation is deterministic from `instance_seed`; answers and evidence come from the finalized timeline metadata.
