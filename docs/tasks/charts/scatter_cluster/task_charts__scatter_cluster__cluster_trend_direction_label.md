# `task_charts__scatter_cluster__cluster_trend_direction_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `cluster_trend_direction_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.cluster_query.ChartsScatterClusterTrendDirectionLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `cluster_trend_direction_label` | `selection.extreme_metric_label` | `string_label` | `keyed_bbox_map` |
