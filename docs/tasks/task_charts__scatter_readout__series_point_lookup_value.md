# `task_charts__scatter_readout__series_point_lookup_value`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `series_pair_value_gap_at_x`, `series_y_anchor_other_series_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.series_readout.ChartsScatterSeriesPointLookupTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
