# `task_charts__scientific_axis_frame__axis_span_value`

## Contract
1. Domain: `charts`
2. Scene id: `scientific_axis_frame`
3. Source implementation domain/group: `charts/scientific`
4. Query ids: `x_axis_span_value`, `y_axis_span_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.axis_frame_query.ChartsScientificAxisFrameAxisSpanValueTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation maps `min_tick` and `max_tick` to the smallest and largest visible tick labels on the requested axis.
4. Decorative plotted data, title text, axis labels, and distractor text are metadata unless explicitly queried.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `x_axis_span_value` | `difference.axis_tick.visible_min_max` | `integer_value` | `keyed_bbox_map` |
| `y_axis_span_value` | `difference.axis_tick.visible_min_max` | `integer_value` | `keyed_bbox_map` |
