# `task_charts__annotated_series__callout_endpoint_change_value`

## Contract
1. Domain: `charts`
2. Scene id: `annotated_series`
3. Source implementation domain/group: `charts/annotated_series`
4. Query id: `callout_endpoint_change_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.annotated_series.event_window_query.ChartsAnnotatedSeriesCalloutEndpointChangeValueTask`
2. Prompt lookup domain/group: `charts/annotated_series`
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
| `callout_endpoint_change_value` | `numeric.difference_or_change` | `integer_value` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
