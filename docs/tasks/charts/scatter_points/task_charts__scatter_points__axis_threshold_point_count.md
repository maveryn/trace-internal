# `task_charts__scatter_points__axis_threshold_point_count`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_points`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `axis_threshold_point_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.points_query.ChartsScatterPointsAxisThresholdPointCountTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation should mark the centers of the counted scatter points only.
4. Renderer context such as legends, axes, threshold guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `axis_threshold_point_count` | `count.points_by_axis_threshold` | `integer_count` | `point_set` |
