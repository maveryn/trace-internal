# `task_charts__surface_3d__series_trend_label`

## Contract
1. Domain: `charts`
2. Scene id: `surface_3d`
3. Public task id: `task_charts__surface_3d__series_trend_label`
4. Query ids: `increase`, `decrease`

## Implementation
1. Registered class: `trace.tasks.charts.surface_3d.series_trend_label.ChartsThreeDSeriesTrendLabelTask`
2. Source file: `trace/tasks/charts/surface_3d/series_trend_label.py`
3. Prompt bundle: `charts_surface_3d_v1`
4. Prompt keys: scene `surface_3d`, task `three_d_chart_query`, query `increase` or `decrease`
5. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
6. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_map`.
3. Annotation maps `start_point` and `end_point` to [x0,y0,x1,y1] pixel boxes around the answer series endpoints.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`selection.extreme_label(difference(endpoint_value(series), start_value(series)), direction); scene=surface_3d; scope=series_trend_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `increase` | `selection.extreme_label(difference(endpoint_value(series), start_value(series)), increase)` | `string_label` | `bbox_map` |
| `decrease` | `selection.extreme_label(difference(endpoint_value(series), start_value(series)), decrease)` | `string_label` | `bbox_map` |
