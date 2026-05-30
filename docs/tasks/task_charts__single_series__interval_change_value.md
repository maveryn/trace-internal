# `task_charts__single_series__interval_change_value`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/trend`
4. Query id: `endpoint_change_value`, `interval_rate_value`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_point_map`.

## Evidence
Prompt-facing evidence uses role-keyed points at the two endpoint marks:
`start_mark` and `end_mark`. Intermediate labels remain trace metadata for
step-count and interval replay.

## Implementation
1. Registered class: `trace.tasks.charts.trend.value.ChartsTrendIntervalChangeValueTask`
2. Prompt lookup domain/group: `charts/trend`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
