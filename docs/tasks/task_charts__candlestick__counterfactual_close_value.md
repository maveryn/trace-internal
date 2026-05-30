# `task_charts__candlestick__counterfactual_close_value`

## Contract
1. Domain: `charts`
2. Scene id: `candlestick`
3. Source implementation domain/group: `charts/candlestick`
4. Query id: `close_after_body_change_value`
5. Semantic query details are recorded in `query_id` and trace params.
6. Answer type: `integer`.
7. Evidence type: `bbox_set` containing one box around the target candle body. Printed O/H/L/C value labels and the period label are support text recorded in trace metadata, not prompt-facing evidence boxes.

## Implementation
1. Registered class: `trace.tasks.charts.candlestick.ohlc_query.ChartsCandlestickCounterfactualCloseValueTask`
2. Prompt lookup domain/group: `charts/candlestick`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
