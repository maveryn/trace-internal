# `task_charts__heatmap__axis_condition_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `heatmap`
3. Source implementation: `trace/tasks/charts/heatmap/axis_condition_extremum_label.py`
4. Query ids: `row_condition_extremum_label`, `column_condition_extremum_label`
5. Query ids bind the prompt-visible axis being selected; sampled condition kind and heatmap style are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.heatmap.axis_condition_extremum_label.ChartsHeatmapAxisConditionExtremumLabelTask`
2. Prompt lookup: `prompts/charts/heatmap/charts_heatmap_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`arg_extreme(axis_label, count(filter(cells_on_axis, condition_kind)), direction=largest); output=string_label; annotation=bbox_set(matching_cells_in_winning_axis); scene=heatmap; scope=axis_condition_extremum_label`

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation marks matching cells in the winning row or column.
4. Axes, legend, title, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `row_condition_extremum_label` | `arg_extreme.axis_condition_count` | `string_label` | `bbox_set` |
| `column_condition_extremum_label` | `arg_extreme.axis_condition_count` | `string_label` | `bbox_set` |
