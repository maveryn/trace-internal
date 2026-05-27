# `task_charts__violin__shape_feature_label`

## Contract
1. Domain: `charts`
2. Scene id: `violin`
3. Source implementation domain/group: `charts/distribution`
4. Query id: `bimodal_label`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.violin_label.ChartsDistributionViolinShapeFeatureLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
