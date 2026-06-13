# `task_charts__candlestick__range_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `candlestick`
3. Source implementation scene package: `charts/candlestick`
4. Query id: sampled from `largest_wick_range_label`, `smallest_wick_range_label`, `largest_body_range_label`, `smallest_body_range_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.candlestick.range_extremum_label.ChartsCandlestickRangeExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/candlestick`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_wick_range_label` | `selection.extreme_metric_label` | `string_label` | `point_set` |
| `smallest_wick_range_label` | `selection.extreme_metric_label` | `string_label` | `point_set` |
| `largest_body_range_label` | `selection.extreme_metric_label` | `string_label` | `point_set` |
| `smallest_body_range_label` | `selection.extreme_metric_label` | `string_label` | `point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
