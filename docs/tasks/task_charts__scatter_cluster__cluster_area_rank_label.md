# `task_charts__scatter_cluster__cluster_area_rank_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Source implementation domain/group: `charts/scatter`
4. Query ids: `largest_cluster_area_label`, `second_largest_cluster_area_label`, `smallest_cluster_area_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.cluster_query.ChartsScatterClusterAreaRankLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the answer cluster's shaded footprint, not the legend row or raw point labels.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_cluster_area_label` | `selection.ranked_item` | `string_label` | `keyed_bbox_map` |
| `second_largest_cluster_area_label` | `selection.ranked_item` | `string_label` | `keyed_bbox_map` |
| `smallest_cluster_area_label` | `selection.ranked_item` | `string_label` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
