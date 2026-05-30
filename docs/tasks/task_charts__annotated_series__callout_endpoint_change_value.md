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
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence Contract
1. Evidence type: `keyed_point_map`.
2. Prompt-facing evidence is a keyed point object with `callout_mark` and `endpoint_mark` mapped to the two value-mark centers used for the absolute change.
3. The callout box, arrow, and callout label box are retained in trace/render metadata as locators, not public evidence.
