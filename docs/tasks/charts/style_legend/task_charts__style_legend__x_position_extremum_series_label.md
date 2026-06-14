# `task_charts__style_legend__x_position_extremum_series_label`

## Contract
1. Domain: `charts`
2. Scene id: `style_legend`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `x_position_extremum_series_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.style_legend_query.ChartsStyleLegendXPositionExtremumSeriesLabelTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation marks the selected plotted marker at the queried x-axis label.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `x_position_highest_series_label` | `argmax(series, value(series, x_position))` | `string_label` | `point_set` |
| `x_position_lowest_series_label` | `argmin(series, value(series, x_position))` | `string_label` | `point_set` |
