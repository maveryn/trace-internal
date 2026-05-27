# `task_charts__candlestick__counterfactual_close_value`

## Contract
1. Domain: `charts`
2. Scene id: `candlestick`
3. Source implementation domain/group: `charts/candlestick`
4. Query id: `close_after_body_change_value`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.candlestick.ohlc_query.ChartsCandlestickCounterfactualCloseValueTask`
2. Prompt lookup domain/group: `charts/candlestick`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
