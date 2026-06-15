# `task_charts__annotated_series__callout_endpoint_change_value`

## Contract
1. Domain: `charts`
2. Scene id: `annotated_series`
3. Source package: `charts/annotated_series`
4. Query id: `single`
5. Semantic query details are recorded in `query_id` and trace params.
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`
8. Endpoint side is an internal generation axis recorded as `endpoint_side=first|last`, not a query id.

## Implementation
1. Registered class: `trace.tasks.charts.annotated_series.callout_endpoint_change_value.ChartsAnnotatedSeriesCalloutEndpointChangeValueTask`
2. Prompt lookup: `prompts/charts/annotated_series/charts_annotated_series_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `absolute_difference(value(mark(role=callout_mark)), value(mark(role=endpoint_mark))); output=integer_value; annotation=keyed_point_map(callout_mark, endpoint_mark); generation_metadata=endpoint_side:{first,last}; scene=annotated_series; scope=callout_endpoint_change_value`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `numeric.callout_endpoint_difference` | `integer_value` | `keyed_point_map` |
