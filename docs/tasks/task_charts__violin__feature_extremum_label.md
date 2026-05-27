# `task_charts__violin__feature_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `violin`
3. Source implementation domain/group: `charts/distribution`
4. Query id: `highest_mode`, `lowest_mode`, `narrowest_support`, `widest_support`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.violin_label.ChartsDistributionViolinFeatureExtremumLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
