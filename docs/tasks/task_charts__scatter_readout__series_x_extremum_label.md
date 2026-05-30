# `task_charts__scatter_readout__series_x_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `series_highest_x_label`, `series_lowest_x_label`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_bbox_map`.

## Evidence
Prompt-facing evidence uses role-keyed boxes over the selected point/value
readout and its shared x-axis label: `target_point_readout` and
`x_axis_label`. Controlled-unanswerable instances use an empty evidence object.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.series_readout.ChartsScatterSeriesExtremumXLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
