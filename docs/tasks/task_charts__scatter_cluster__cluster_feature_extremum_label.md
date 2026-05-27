# `task_charts__scatter_cluster__cluster_feature_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_cluster`
3. Source implementation domain/group: `charts/scatter`
4. Query id: `cluster_separation_extremum_label`, `cluster_spread_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.cluster_query.ChartsScatterClusterFeatureExtremumLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
