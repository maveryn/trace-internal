# `task_pages__hero_callout_infographic__callout_condition_count`

## Identity
1. Domain: `pages`
2. Scene id: `hero_callout_infographic`
3. Source task group: `infographic`
4. Task id: `task_pages__hero_callout_infographic__callout_condition_count`

## Contract
1. Objective: count callout cards whose visible value for a requested field satisfies one threshold condition.
2. Branch metadata: `query_id`
3. `query_id`: `callout_condition_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over the matching value cells.
6. Query knobs: target field label, condition operator, threshold, callout count, per-callout field count, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `hero_callout_infographic`
3. Task key: `hero_callout_infographic_query`
4. Internal prompt variant key: `callout_condition_count`
5. Trace records the threshold, operator, candidate callout values, matching values, sampled visual assets, sampled style metadata, final bboxes, and layout geometry.
6. Threshold sampling keeps the answer nonzero and not all visible callouts for the selected field.

## Rendering Notes
1. This task reuses the hero-callout infographic renderer, layout variants, and pages-owned visual asset pool.
2. Decorative assets and connector lines are not annotation; only matching value cells are prompt-facing annotation.
