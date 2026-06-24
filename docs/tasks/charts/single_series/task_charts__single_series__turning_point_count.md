# `task_charts__single_series__turning_point_count`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/turning_point_count.py`
4. Public task id: `task_charts__single_series__turning_point_count`
5. Supported `query_id` values: `peak_turning_point_count`, `trough_turning_point_count`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.turning_point_count.ChartsTrendTurningPointCountTask`
2. Prompt lookup: `prompts/charts/single_series/charts_trend_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`count(turning_points(sequence(values), turning_kind)); output=integer_count; annotation=point_set(turning_points); scene=single_series; scope=turning_point_count`

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation marks every local peak or trough point counted by the selected query.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `peak_turning_point_count` | `count.local_peaks` | `integer_count` | `point_set` |
| `trough_turning_point_count` | `count.local_troughs` | `integer_count` | `point_set` |
