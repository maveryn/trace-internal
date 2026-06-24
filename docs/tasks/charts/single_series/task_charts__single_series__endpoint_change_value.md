# `task_charts__single_series__endpoint_change_value`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/endpoint_change_value.py`
4. Public task id: `task_charts__single_series__endpoint_change_value`
5. Supported `query_id` values: `absolute_endpoint_change_value`, `signed_endpoint_change_value`, `percent_endpoint_change_value`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.endpoint_change_value.ChartsTrendEndpointChangeValueTask`
2. Prompt lookup: `prompts/charts/single_series/charts_trend_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`difference(value(end_mark), value(start_mark), mode); output=integer_value; annotation=point_map(start_mark,end_mark); scene=single_series; scope=endpoint_change_value`

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_map`.
3. Annotation maps `start_mark` and `end_mark` to the two endpoint mark points named by the prompt.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `absolute_endpoint_change_value` | `difference.endpoint_value_absolute` | `integer_value` | `point_map` |
| `signed_endpoint_change_value` | `difference.endpoint_value_signed` | `integer_value` | `point_map` |
| `percent_endpoint_change_value` | `difference.endpoint_value_percent` | `integer_value` | `point_map` |
