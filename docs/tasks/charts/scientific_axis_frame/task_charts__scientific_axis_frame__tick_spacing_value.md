# `task_charts__scientific_axis_frame__tick_spacing_value`

## Contract
1. Domain: `charts`
2. Scene id: `scientific_axis_frame`
3. Source implementation domain/scene: `charts/scientific_axis_frame`
4. Supported `query_id` values: `x_tick_spacing_value`, `y_tick_spacing_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Program Contract
`difference(next_adjacent_tick(axis), first_adjacent_tick(axis)); output=integer_value; annotation=bbox_map(first_tick,next_tick); scene=scientific_axis_frame; scope=tick_spacing_value`

## Implementation
1. Registered class: `trace.tasks.charts.scientific_axis_frame.tick_spacing_value.ChartsScientificAxisFrameTickSpacingValueTask`
2. Prompt lookup domain/scene: `charts/scientific_axis_frame`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_map`.
3. Annotation maps `first_tick` and `next_tick` to the lower-value highlighted tick label and the next higher highlighted tick label.
4. Decorative plotted data, axis labels, and distractor text are metadata unless explicitly queried.
5. Scalar annotation conversion is not applicable because this task has two role-bound tick-label witnesses.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `x_tick_spacing_value` | `axis=x` | `integer_value` | `bbox_map` |
| `y_tick_spacing_value` | `axis=y` | `integer_value` | `bbox_map` |
