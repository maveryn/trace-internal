# `task_charts__scatter_cluster__centroid_option_selection_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Task id: `task_charts__scatter_cluster__centroid_option_selection_label`
4. Supported `query_id`s: `single`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_cluster.centroid_option_selection_label.ChartsScatterClusterCentroidOptionSelectionLabelTask`
2. Prompt bundle: `prompts/charts/scatter_cluster/charts_scatter_cluster_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.

## Program Contract
`argmin_label(option, distance(point(option), centroid(target_cluster))); scene=scatter_cluster; scope=centroid_option_selection_label`

## Annotation Contract
1. Answer schema: `option_letter`.
2. Annotation schema: `bbox_map`.
3. The rendered centroid-option markers use either `4` labels (`A..D`) or `6` labels (`A..F`) by construction.
4. Annotation should map `target_cluster` to the named cluster hull and `selected_option_marker` to the selected option marker bbox.
5. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `target_cluster=sampled; option_set=4_or_6_markers` | `option_letter` | `bbox_map` |
