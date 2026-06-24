# `task_charts__scatter_points__category_axis_mean_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_points`
3. Public task id: `task_charts__scatter_points__category_axis_mean_extremum_label`
4. Query ids encode the mean axis and extremum direction because both change prompt wording and program arguments.

## Program Contract
- `argextreme_label(category, mean(coord(points(category), axis)), direction); output=string_label; annotation=point_set(answer_category_point_centers); scene=scatter_points; scope=category_axis_mean_extremum_label`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_points.category_axis_mean_extremum_label.ChartsScatterPointsCategoryAxisMeanExtremumLabelTask`
2. Prompt bundle: `prompts/charts/scatter_points/charts_scatter_points_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation marks the centers of all scatter points in the answer category.
4. Axes, legends, category labels, titles, and distractor text are not annotation targets.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_mean_x_category_label` | `axis=x`, `direction=largest` | `string_label` | `point_set` |
| `smallest_mean_x_category_label` | `axis=x`, `direction=smallest` | `string_label` | `point_set` |
| `largest_mean_y_category_label` | `axis=y`, `direction=largest` | `string_label` | `point_set` |
| `smallest_mean_y_category_label` | `axis=y`, `direction=smallest` | `string_label` | `point_set` |
