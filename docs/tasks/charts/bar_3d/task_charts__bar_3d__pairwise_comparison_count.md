# `task_charts__bar_3d__pairwise_comparison_count`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation scene package: `charts/bar_3d`
4. Query id: `single`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.bar_3d.pairwise_comparison_count.ChartsThreeDBarPairwiseComparisonCountTask`
2. Prompt lookup scene: `charts/bar_3d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `segment_set`.
3. Annotation is a `segment_set`; each segment is `[[x1, y1], [x2, y2]]` and connects the top-center points of the two compared bars for one counted category.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(category where compare(value(category,series_a), value(category,series_b), relation=greater_than)); output=integer_count; annotation=point_set(comparison_bar_top_centers); scene=bar_3d; scope=pairwise_comparison_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count.pairwise_series_comparison` | `integer_count` | `segment_set` |
