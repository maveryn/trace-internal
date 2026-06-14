# `task_charts__heatmap__axis_cell_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `heatmap`
3. Source implementation: `trace/tasks/charts/heatmap/axis_cell_extremum_label.py`
4. Query ids: `row_hottest_column_label`, `row_coolest_column_label`, `column_hottest_row_label`, `column_coolest_row_label`
5. Query ids bind prompt-visible axis and extremum direction; sampled label names and heatmap style are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.heatmap.axis_cell_extremum_label.ChartsHeatmapAxisCellExtremumLabelTask`
2. Prompt lookup: `prompts/charts/heatmap/charts_heatmap_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`arg_extreme(opposite_axis_label, heat_value(cell(named_axis_label, opposite_axis_label)), direction={hottest,coolest}); output=string_label; annotation=bbox_set(candidate_cells_on_named_axis); scene=heatmap; scope=axis_cell_extremum_label`

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation marks all candidate cells in the named row or column.
4. Axes, legend, title, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `row_hottest_column_label` | `arg_extreme.cell_value_on_named_axis` | `string_label` | `bbox_set` |
| `row_coolest_column_label` | `arg_extreme.cell_value_on_named_axis` | `string_label` | `bbox_set` |
| `column_hottest_row_label` | `arg_extreme.cell_value_on_named_axis` | `string_label` | `bbox_set` |
| `column_coolest_row_label` | `arg_extreme.cell_value_on_named_axis` | `string_label` | `bbox_set` |
