# `task_charts__style_legend__threshold_series_count`

## Contract
1. Domain: `charts`
2. Scene id: `style_legend`
3. Public task id: `task_charts__style_legend__threshold_series_count`
4. Supported `query_id`: `above_threshold_series_count`, `below_threshold_series_count`

## Implementation
1. Registered class: `trace.tasks.charts.style_legend.threshold_series_count.ChartsStyleLegendThresholdSeriesCountTask`
2. Prompt bundle: `charts_style_legend_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation marks each counted plotted marker at the queried x-axis label; use an empty array when the count is zero.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`count(filter(series, compare(value(series, x_position), threshold, comparator={above,below}))); output=integer_count; annotation=point_set; scene=style_legend; scope=threshold_series_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `above_threshold_series_count` | `count(series where value(series, x_position) > threshold)` | `integer_count` | `point_set` |
| `below_threshold_series_count` | `count(series where value(series, x_position) < threshold)` | `integer_count` | `point_set` |
