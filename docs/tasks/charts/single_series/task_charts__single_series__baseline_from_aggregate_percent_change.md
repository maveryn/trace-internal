# `task_charts__single_series__baseline_from_aggregate_percent_change`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/baseline_from_aggregate_percent_change.py`
4. Public task id: `task_charts__single_series__baseline_from_aggregate_percent_change`
5. Supported `query_id` values: `single`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.baseline_from_aggregate_percent_change.ChartsHypotheticalBaselineFromAggregatePercentChangePublicTask`
2. Prompt lookup: `prompts/charts/single_series/charts_hypothetical_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`solve_baseline(sum(values(aggregate_labels)), percent_above_baseline); output=integer_value; annotation=point_set(aggregate_marks); scene=single_series; scope=baseline_from_aggregate_percent_change`

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation marks the visible aggregate marks used in the baseline equation.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `solve_baseline.aggregate_percent_higher_than_baseline` | `integer_value` | `point_set` |
