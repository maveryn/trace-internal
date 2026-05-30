# `task_charts__single_series__turning_point_count`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/trend`
4. Query id: `turning_point_count`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `point_set`.

## Evidence
Prompt-facing evidence is a homogeneous `point_set` over every matching local
turning point. Evidence cardinality equals the integer answer.

## Implementation
1. Registered class: `trace.tasks.charts.trend.value.ChartsTrendTurningPointCountTask`
2. Prompt lookup domain/group: `charts/trend`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
