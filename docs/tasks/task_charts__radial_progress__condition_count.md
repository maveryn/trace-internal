# `task_charts__radial_progress__condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `radial_progress`
3. Source implementation domain/group: `charts/radial_progress`
4. Query id: `at_least_threshold_count`, `below_threshold_count`, `remaining_at_least_threshold_count`, `within_range_count`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.radial_progress.progress_chart.ChartsRadialProgressConditionCountTask`
2. Prompt lookup domain/group: `charts/radial_progress`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
