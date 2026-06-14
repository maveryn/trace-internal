# `task_charts__bar_3d__pairwise_comparison_count`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation scene package: `charts/bar_3d`
4. Query id: `series_comparison_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.bar_3d.pairwise_comparison_count.ChartsThreeDBarPairwiseComparisonCountTask`
2. Prompt lookup scene: `charts/bar_3d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_pair_set`.
3. Annotation marks paired top-center bar points for each compared category.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `series_comparison_count` | `count.pairwise_comparison` | `integer_count` | `point_pair_set` |
