# `task_charts__scatter_cluster__centroid_option_selection_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `centroid_option_selection_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.cluster_query.ChartsScatterClusterCentroidOptionSelectionLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `option_letter`.
2. Annotation schema: `keyed_bbox_map`.
3. The rendered centroid-option markers use either `4` labels (`A..D`) or `6` labels (`A..F`) by construction.
4. Annotation should mark the target cluster hull and selected option marker bbox.
5. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `centroid_option_selection_label` | `selection.nearest_option_to_centroid` | `option_letter` | `keyed_bbox_map` |
