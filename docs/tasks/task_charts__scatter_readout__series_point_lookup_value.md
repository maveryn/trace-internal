# `task_charts__scatter_readout__series_point_lookup_value`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `series_pair_value_gap_at_x`, `series_y_anchor_other_series_value`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_bbox_map`.

## Evidence
Prompt-facing evidence uses role-keyed boxes over the selected point/value
readouts and the shared x-axis label: `target_point_readout`,
`comparison_point_readout`, and `x_axis_label`.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.series_readout.ChartsScatterSeriesPointLookupTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
