# `task_charts__single_series__order_statistic_value`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/statistics`
4. Query id: `order_statistic_value`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `point_set`.

## Evidence
Prompt-facing evidence is a one-point `point_set` at the center of the mark
whose value is the requested order statistic.

## Implementation
1. Registered class: `trace.tasks.charts.statistics.summary_query.ChartsSingleSeriesOrderStatisticValueTask`
2. Prompt lookup domain/group: `charts/statistics`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
