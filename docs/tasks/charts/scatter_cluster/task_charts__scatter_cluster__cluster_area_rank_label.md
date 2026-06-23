# `task_charts__scatter_cluster__cluster_area_rank_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Task id: `task_charts__scatter_cluster__cluster_area_rank_label`
4. Supported `query_id`s: `largest_cluster_area_label`, `second_largest_cluster_area_label`, `smallest_cluster_area_label`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_cluster.cluster_area_rank_label.ChartsScatterClusterAreaRankLabelTask`
2. Prompt bundle: `prompts/charts/scatter_cluster/charts_scatter_cluster_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.

## Program Contract
`ranked_label(cluster, footprint_area(cluster), rank); scene=scatter_cluster; scope=cluster_area_rank_label`

## Annotation Contract
1. Answer schema: `string`.
2. Annotation schema: `bbox`.
3. Annotation should mark the answer cluster's shaded footprint, not the legend row or raw point labels.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_cluster_area_label` | `rank=largest` | `string` | `bbox` |
| `second_largest_cluster_area_label` | `rank=second_largest` | `string` | `bbox` |
| `smallest_cluster_area_label` | `rank=smallest` | `string` | `bbox` |
