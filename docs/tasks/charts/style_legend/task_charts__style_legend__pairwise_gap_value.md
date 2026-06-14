# `task_charts__style_legend__pairwise_gap_value`

## Contract
1. Domain: `charts`
2. Scene id: `style_legend`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `pairwise_gap_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.style_legend_query.ChartsStyleLegendPairwiseGapValueTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation marks the two plotted markers used to compute the absolute gap.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `pairwise_gap_value` | `abs(value(series_a, x_position) - value(series_b, x_position))` | `integer_value` | `point_set` |
