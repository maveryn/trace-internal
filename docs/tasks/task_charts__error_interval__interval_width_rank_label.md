# `task_charts__error_interval__interval_width_rank_label`

## Contract
1. Domain: `charts`
2. Scene id: `error_interval`
3. Source implementation domain/group: `charts/error_interval`
4. Query id: `narrowest_interval_label`, `second_narrowest_interval_label`, `second_widest_interval_label`, `widest_interval_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.error_interval.interval_chart.ChartsErrorIntervalRelationLabelTask`
2. Prompt lookup domain/group: `charts/error_interval`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
