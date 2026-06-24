# `task_charts__scatter_readout__series_x_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Public task id: `task_charts__scatter_readout__series_x_extremum_label`
4. Supported `query_id` values: `series_highest_x_label`, `series_lowest_x_label`
5. The query id changes the visible extremum direction in the prompt and the program argument.

## Program Contract
- `select_label(x_label(arg_extreme(point in series, y_value(point), direction))); output=string_label; annotation=bbox_map(target_point_readout,x_axis_label); scene=scatter_readout; scope=series_x_extremum_label`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_readout.series_x_extremum_label.ChartsScatterSeriesExtremumXLabelTask`
2. Prompt bundle: `prompts/charts/scatter_readout/charts_scatter_readout_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_map`.
3. Annotation maps `target_point_readout` and `x_axis_label` to the supporting [x0,y0,x1,y1] pixel boxes.
4. If the sampled branch is unanswerable because the requested series is absent from the legend, annotation is an empty object.
5. Axes, legends, titles, and distractor text are metadata unless named as one of the annotation roles.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `series_highest_x_label` | `direction=highest` | `string_label` | `bbox_map` |
| `series_lowest_x_label` | `direction=lowest` | `string_label` | `bbox_map` |
