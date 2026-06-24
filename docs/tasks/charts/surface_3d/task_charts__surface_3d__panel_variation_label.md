# `task_charts__surface_3d__panel_variation_label`

## Contract
1. Domain: `charts`
2. Scene id: `surface_3d`
3. Public task id: `task_charts__surface_3d__panel_variation_label`
4. Query ids: `single`

## Implementation
1. Registered class: `trace.tasks.charts.surface_3d.panel_variation_label.ChartsThreeDPanelVariationLabelTask`
2. Source file: `trace/tasks/charts/surface_3d/panel_variation_label.py`
3. Prompt bundle: `charts_surface_3d_v1`
4. Prompt keys: scene `surface_3d`, task `three_d_chart_query`, query `panel_variation_label`
5. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
6. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox`.
3. Annotation marks one [x0,y0,x1,y1] pixel box around the selected panel.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`selection.extreme_label(range(values(panel)), largest); scene=surface_3d; scope=panel_variation_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `selection.extreme_label(range(values(panel)), largest)` | `string_label` | `bbox` |
