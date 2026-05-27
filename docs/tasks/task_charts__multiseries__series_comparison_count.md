# `task_charts__multiseries__series_comparison_count`

## Contract
1. Domain: `charts`
2. Scene id: `multiseries`
3. Source implementation domain/group: `charts/multiseries`
4. Query id: `series_comparison_count`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.multiseries.comparison_query.ChartsMultiseriesSeriesComparisonCountTask`
2. Prompt lookup domain/group: `charts/multiseries`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
