# `task_charts__single_series__interval_rate_value`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/interval_rate_value.py`
4. Public task id: `task_charts__single_series__interval_rate_value`
5. Supported `query_id` values: `single`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.interval_rate_value.ChartsTrendIntervalRateValueTask`
2. Prompt lookup: `prompts/charts/single_series/charts_trend_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`quotient(value(end_mark)-value(start_mark), step_count(start_mark,end_mark)); output=integer_value; annotation=point_map(start_mark,end_mark); scene=single_series; scope=interval_rate_value`

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_map`.
3. Annotation maps `start_mark` and `end_mark` to the two endpoint mark points named by the prompt.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `quotient.endpoint_delta_by_step_count` | `integer_value` | `point_map` |
