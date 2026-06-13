# `task_charts__dashboard__dual_source_target_sum_value`

## Contract
1. Domain: `charts`
2. Scene id: `dashboard`
3. Source implementation domain/group: `charts/dashboard`
4. Query id: sampled from `first_largest_second_smallest_target_sum_value`, `first_smallest_second_largest_target_sum_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dashboard.dual_source_target_sum_value.ChartsDashboardDualSourceTargetSumValueTask`
2. Prompt lookup domain/group: `charts/dashboard`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `first_largest_second_smallest_target_sum_value` | `numeric.aggregate_sum` | `integer_value` | `keyed_point_map` |
| `first_smallest_second_largest_target_sum_value` | `numeric.aggregate_sum` | `integer_value` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
