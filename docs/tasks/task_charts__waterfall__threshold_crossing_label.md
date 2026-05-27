# `task_charts__waterfall__threshold_crossing_label`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation domain/group: `charts/waterfall`
4. Query id: `first_total_at_least_threshold`, `first_total_at_most_threshold`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.panel_query.ChartsWaterfallThresholdCrossingLabelTask`
2. Prompt lookup domain/group: `charts/waterfall`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
