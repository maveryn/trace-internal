# `task_charts__scatter_cluster__cluster_separation_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Task id: `task_charts__scatter_cluster__cluster_separation_extremum_label`
4. Supported `query_id`s: `closest_to_reference_label`, `farthest_from_reference_label`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_cluster.cluster_separation_extremum_label.ChartsScatterClusterSeparationExtremumLabelTask`
2. Prompt bundle: `prompts/charts/scatter_cluster/charts_scatter_cluster_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.

## Program Contract
`argextreme_label(cluster, distance(center(cluster), center(reference_cluster)), direction); scene=scatter_cluster; scope=cluster_separation_extremum_label`

## Annotation Contract
1. Answer schema: `string`.
2. Annotation schema: `bbox_map`.
3. Annotation should map `reference_cluster` and `answer_cluster` to their cluster-hull pixel boxes.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `closest_to_reference_label` | `direction=closest` | `string` | `bbox_map` |
| `farthest_from_reference_label` | `direction=farthest` | `string` | `bbox_map` |
