# `task_charts__style_legend__threshold_series_count`

## Contract
1. Domain: `charts`
2. Scene id: `style_legend`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `threshold_series_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.style_legend_query.ChartsStyleLegendThresholdSeriesCountTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation marks each counted plotted marker at the queried x-axis label; use an empty array when the count is zero.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `above_threshold_series_count` | `count(series where value(series, x_position) > threshold)` | `integer_count` | `point_set` |
| `below_threshold_series_count` | `count(series where value(series, x_position) < threshold)` | `integer_count` | `point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
