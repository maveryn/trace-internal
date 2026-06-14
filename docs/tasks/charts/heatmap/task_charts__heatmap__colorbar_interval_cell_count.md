# `task_charts__heatmap__colorbar_interval_cell_count`

## Contract
1. Domain: `charts`
2. Scene id: `heatmap`
3. Source implementation: `trace/tasks/charts/heatmap/colorbar_interval_cell_count.py`
4. Query id: `single`
5. Interval bounds are sampled generation parameters, not public query branches.

## Implementation
1. Registered class: `trace.tasks.charts.heatmap.colorbar_interval_cell_count.ChartsHeatmapColorbarIntervalCellCountTask`
2. Prompt lookup: `prompts/charts/heatmap/charts_heatmap_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`count(filter(cells, lower_bound <= colorbar_value(cell) <= upper_bound)); output=integer_count; annotation=bbox_set(counted_cells); scene=heatmap; scope=colorbar_interval_cell_count`

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks exactly the counted cells in row-major order.
4. Colorbar, axes, labels, titles, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count.cells.colorbar_interval` | `integer_count` | `bbox_set` |
