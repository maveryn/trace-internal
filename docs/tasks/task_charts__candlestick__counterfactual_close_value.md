# `task_charts__candlestick__counterfactual_close_value`

## Contract
1. Domain: `charts`
2. Scene id: `candlestick`
3. Source implementation scene package: `charts/candlestick`
4. Query id: sampled from `close_after_body_increase_value`, `close_after_body_decrease_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.candlestick.counterfactual_close_value.ChartsCandlestickCounterfactualCloseValueTask`
2. Prompt lookup domain/scene: `charts/candlestick`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `close_after_body_increase_value` | `counterfactual.transform_then_answer` | `integer_value` | `bbox_set` |
| `close_after_body_decrease_value` | `counterfactual.transform_then_answer` | `integer_value` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
