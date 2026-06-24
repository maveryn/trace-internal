# `task_charts__single_series__projected_threshold_crossing_label`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/projected_threshold_crossing_label.py`
4. Public task id: `task_charts__single_series__projected_threshold_crossing_label`
5. Supported `query_id` values: `projected_above_threshold_crossing_label`, `projected_below_threshold_crossing_label`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.projected_threshold_crossing_label.ChartsTrendProjectedThresholdCrossingLabelTask`
2. Prompt lookup: `prompts/charts/single_series/charts_trend_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`first_future_label(linear_project(sequence(values), comparison, threshold)); output=string_label; annotation=point_set(last_observed_marks_and_projected_slots); scene=single_series; scope=projected_threshold_crossing_label`

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation marks the last observed support marks and projected slots needed to witness the crossing.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `projected_above_threshold_crossing_label` | `first_label.linear_projection_crosses_above_threshold` | `string_label` | `point_set` |
| `projected_below_threshold_crossing_label` | `first_label.linear_projection_crosses_below_threshold` | `string_label` | `point_set` |
