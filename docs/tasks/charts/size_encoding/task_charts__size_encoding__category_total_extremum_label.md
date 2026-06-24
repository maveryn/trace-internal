# `task_charts__size_encoding__category_total_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `size_encoding`
3. Source implementation: `trace/tasks/charts/size_encoding/category_total_extremum_label.py`
4. Supported `query_id` values: `largest_category_total_label`, `smallest_category_total_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.size_encoding.category_total_extremum_label.ChartsSizeEncodingCategoryTotalExtremumLabelTask`
2. Prompt lookup domain/group: `charts/size_encoding`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation marks every displayed item belonging to the answer category.
4. Renderer context such as legends, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`select_label(arg_extreme(categories, sum(encoded_value(items_in_category)), direction)); output=string_label; annotation=bbox_set(answer_category_items); scene=size_encoding; scope=category_total_extremum_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_category_total_label` | `selection.extreme_metric_label` | `string_label` | `bbox_set` |
| `smallest_category_total_label` | `selection.extreme_metric_label` | `string_label` | `bbox_set` |
