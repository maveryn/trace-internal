# `task_charts__style_legend__pairwise_gap_value`

## Contract
1. Domain: `charts`
2. Scene id: `style_legend`
3. Public task id: `task_charts__style_legend__pairwise_gap_value`
4. Supported `query_id`: `single`

## Implementation
1. Registered class: `trace.tasks.charts.style_legend.pairwise_gap_value.ChartsStyleLegendPairwiseGapValueTask`
2. Prompt bundle: `charts_style_legend_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation marks the two plotted markers used to compute the absolute gap.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`abs_difference(value(series_a, x_position), value(series_b, x_position)); output=integer_value; annotation=point_set; scene=style_legend; scope=pairwise_gap_value`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `abs_difference(value(series_a, x_position), value(series_b, x_position))` | `integer_value` | `point_set` |
