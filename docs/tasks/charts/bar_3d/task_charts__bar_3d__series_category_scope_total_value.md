# `task_charts__bar_3d__series_category_scope_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation scene package: `charts/bar_3d`
4. Query ids: `series_total_value`, `series_interval_total_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.bar_3d.series_category_scope_total_value.ChartsThreeDBarSeriesCategoryScopeTotalValueTask`
2. Prompt lookup scene: `charts/bar_3d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `sum(value(category,series_label) for category in selected_category_scope); output=integer_value; annotation=point_set(selected_bar_top_centers); scene=bar_3d; scope=series_category_scope_total_value; category_scope={all,contiguous_interval}`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `series_total_value` | `numeric.series_category_scope_sum` | `integer_value` | `point_set` |
| `series_interval_total_value` | `numeric.series_category_scope_sum` | `integer_value` | `point_set` |
