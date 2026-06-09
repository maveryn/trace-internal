# `task_charts__scientific_axis_frame__tick_spacing_value`

## Contract
1. Domain: `charts`
2. Scene id: `scientific_axis_frame`
3. Source implementation domain/group: `charts/scientific`
4. Query ids: `x_tick_spacing_value`, `y_tick_spacing_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.axis_frame_query.ChartsScientificAxisFrameTickSpacingValueTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation maps `first_tick` and `next_tick` to the lower-value highlighted tick label and the next higher highlighted tick label.
4. Decorative plotted data, title text, axis labels, and distractor text are metadata unless explicitly queried.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `x_tick_spacing_value` | `difference.axis_tick.adjacent_pair` | `integer` | `keyed_bbox_map` |
| `y_tick_spacing_value` | `difference.axis_tick.adjacent_pair` | `integer` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
