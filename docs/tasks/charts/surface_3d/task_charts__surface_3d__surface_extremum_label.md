# `task_charts__surface_3d__surface_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `surface_3d`
3. Public task id: `task_charts__surface_3d__surface_extremum_label`
4. Query ids: `highest`, `lowest`

## Implementation
1. Registered class: `trace.tasks.charts.surface_3d.surface_extremum_label.ChartsThreeDSurfaceExtremumLabelTask`
2. Source file: `trace/tasks/charts/surface_3d/surface_extremum_label.py`
3. Prompt bundle: `charts_surface_3d_v1`
4. Prompt keys: scene `surface_3d`, task `three_d_chart_query`, query `surface_highest_value` or `surface_lowest_value`
5. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
6. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox`.
3. Annotation marks one [x0,y0,x1,y1] pixel box around the selected surface-cell marker.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`selection.extreme_label(value(surface_cell), direction); scene=surface_3d; scope=surface_extremum_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest` | `selection.extreme_label(value(surface_cell), highest)` | `string_label` | `bbox` |
| `lowest` | `selection.extreme_label(value(surface_cell), lowest)` | `string_label` | `bbox` |
