# `task_charts__errorbar_series__bound_extremum_x_label`

## Contract
1. Domain: `charts`
2. Scene id: `errorbar_series`
3. Source implementation domain/group: `charts/errorbar_series`
4. Query id: `bound_extremum_x_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.errorbar_series.series_query.ChartsErrorbarSeriesBoundExtremumXLabelTask`
2. Prompt lookup domain/group: `charts/errorbar_series`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation maps `selected_bound_endpoint` to the pixel point on the selected error-bar bound endpoint.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest_upper_bound_x_label` | `argmax_x_label(upper_bound(errorbar(target_series, x_position)))` | `string_label` | `keyed_point_map` |
| `lowest_lower_bound_x_label` | `argmin_x_label(lower_bound(errorbar(target_series, x_position)))` | `string_label` | `keyed_point_map` |
