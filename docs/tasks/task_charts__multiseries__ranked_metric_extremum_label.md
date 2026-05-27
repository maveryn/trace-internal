# `task_charts__multiseries__ranked_metric_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `multiseries`
3. Source implementation domain/group: `charts/multiseries`
4. Query id: `ranked_change_extremum`, `ranked_ratio_extremum`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.multiseries.comparison_query.ChartsMultiseriesRankedMetricExtremumTask`
2. Prompt lookup domain/group: `charts/multiseries`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
