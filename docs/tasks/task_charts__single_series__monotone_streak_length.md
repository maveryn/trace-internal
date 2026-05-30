# `task_charts__single_series__monotone_streak_length`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/trend`
4. Query id: `longest_monotone_streak`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `point_set`.

## Evidence
Prompt-facing evidence is a homogeneous `point_set` over every mark in the
unique longest monotone streak. Evidence cardinality equals the integer answer.

## Implementation
1. Registered class: `trace.tasks.charts.trend.value.ChartsTrendMonotoneStreakLengthTask`
2. Prompt lookup domain/group: `charts/trend`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
