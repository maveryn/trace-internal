# `task_charts__bar_3d__category_extremum_gap_value`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation scene package: `charts/bar_3d`
4. Query id: `category_extremum_gap_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.bar_3d.category_extremum_gap_value.ChartsThreeDBarCategoryExtremumGapValueTask`
2. Prompt lookup scene: `charts/bar_3d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_map`.
3. Annotation marks the top-center points of the highest and lowest bars in the requested category using keys `highest` and `lowest`.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `category_extremum_gap_value` | `numeric.ranked_difference` | `integer_value` | `keyed_point_map` |
