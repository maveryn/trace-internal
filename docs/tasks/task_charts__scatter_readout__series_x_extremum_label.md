# `task_charts__scatter_readout__series_x_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `series_highest_x_label`, `series_lowest_x_label`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.series_readout.ChartsScatterSeriesExtremumXLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
