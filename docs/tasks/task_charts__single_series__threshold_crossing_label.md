# `task_charts__single_series__threshold_crossing_label`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/trend`
4. Query id: `threshold_crossing`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.trend.value.ChartsTrendThresholdCrossingLabelTask`
2. Prompt lookup domain/group: `charts/trend`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
