# `task_charts__heatmap__colorbar_threshold_cell_count`

## Contract
1. Domain: `charts`
2. Scene id: `heatmap`
3. Source implementation domain/group: `charts/heatmap`
4. Query ids: `colorbar_above_threshold_cell_count`, `colorbar_below_threshold_cell_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.heatmap.grid_query.ChartsHeatmapColorbarThresholdCellCountTask`
2. Prompt lookup domain/group: `charts/heatmap`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks exactly the counted cells in row-major order.
4. Colorbar, axes, labels, titles, and distractor text are metadata unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `colorbar_above_threshold_cell_count` | `count.cells.colorbar_threshold` | `integer_count` | `bbox_set` |
| `colorbar_below_threshold_cell_count` | `count.cells.colorbar_threshold` | `integer_count` | `bbox_set` |
