# `task_charts__curve_panels__threshold_series_count`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `threshold_series_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.multipanel_subplot_query.ChartsScientificThresholdSeriesCountTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence
1. Evidence type: `point_set`.
2. Points mark the method markers above the threshold at the queried x-value.
