# `task_charts__boxplot__median_rank_difference_value`

## Contract
1. Domain: `charts`
2. Scene id: `boxplot`
3. Source implementation scene package: `charts/boxplot`
4. Query id: sampled from `median_top_bottom_difference_value`, `median_top_second_difference_value`, `median_top_third_difference_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.boxplot.median_rank_difference_value.ChartsDistributionBoxplotMedianRankDifferenceValueTask`
2. Prompt lookup scene package: `charts/boxplot`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `median_top_bottom_difference_value` | `numeric.ranked_difference` | `integer_value` | `keyed_point_map` |
| `median_top_second_difference_value` | `numeric.ranked_difference` | `integer_value` | `keyed_point_map` |
| `median_top_third_difference_value` | `numeric.ranked_difference` | `integer_value` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
