# `task_charts__candlestick__range_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `candlestick`
3. Source implementation domain/group: `charts/candlestick`
4. Query id: sampled from `body_range_extremum_label`, `wick_range_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.candlestick.ohlc_query.ChartsCandlestickRangeExtremumLabelTask`
2. Prompt lookup domain/group: `charts/candlestick`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `mixed_annotation_schema:bbox_set|point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `body_range_extremum_label` | `selection.extreme_metric_label` | `string_label` | `mixed_annotation_schema:bbox_set|point_set` |
| `wick_range_extremum_label` | `selection.extreme_metric_label` | `string_label` | `mixed_annotation_schema:bbox_set|point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
