# `task_charts__errorbar_series__threshold_support_count`

## Contract
1. Domain: `charts`
2. Scene id: `errorbar_series`
3. Source implementation domain/group: `charts/errorbar_series`
4. Query id: `threshold_support_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.errorbar_series.series_query.ChartsErrorbarSeriesThresholdSupportCountTask`
2. Prompt lookup domain/group: `charts/errorbar_series`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks one box around each counted error-bar mark for the named series.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `entirely_above_threshold_count` | `count(x_position where lower_bound(errorbar(target_series, x_position)) > threshold)` | `integer_count` | `bbox_set` |
| `entirely_below_threshold_count` | `count(x_position where upper_bound(errorbar(target_series, x_position)) < threshold)` | `integer_count` | `bbox_set` |
| `contains_threshold_count` | `count(x_position where lower_bound(errorbar(target_series, x_position)) <= threshold <= upper_bound(errorbar(target_series, x_position)))` | `integer_count` | `bbox_set` |
