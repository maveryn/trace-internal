# `task_charts__histogram__interval_value`

## Contract
1. Domain: `charts`
2. Scene id: `histogram`
3. Source implementation domain/group: `charts/distribution`
4. Query id: `bin_count_between_values`, `interval_mass`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.histogram_count.ChartsDistributionHistogramIntervalValueTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
