# `task_pages__hero_callout_infographic__callout_metric_extremum_label`

## Identity
1. Domain: `pages`
2. Scene id: `hero_callout_infographic`
3. Source scene: `infographic`
4. Task id: `task_pages__hero_callout_infographic__callout_metric_extremum_label`

## Contract
1. Objective: identify the callout title with the highest or lowest visible value for a requested field across the callout cards.
2. Branch metadata: `query_id`
3. `query_id`: `callout_metric_extremum_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `winning_callout_title`, `winning_field_label`, `winning_value`, and `candidate_N` compared-value boxes.
6. Query knobs: target field label, rank direction, callout count, per-callout field count, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `hero_callout_infographic`
3. Task key: `hero_callout_infographic_query`
4. Internal prompt variant key: `callout_metric_extremum_label`
5. Trace records the compared callout values, parsed numeric values, rank direction, selected winner, sampled visual assets, sampled style metadata, final bboxes, and layout geometry.
6. Generation guarantees that the selected field has at least three visible candidates and a unique extremum.

## Rendering Notes
1. This task reuses the hero-callout infographic renderer, layout variants, and pages-owned visual asset pool.
2. Annotation stays on the compared field/value witnesses and the winning callout title; the hero asset, badges, and connectors are visual context only.
