# `task_charts__violin__distribution_feature_label`

## Contract
1. Domain: `charts`
2. Scene id: `violin`
3. Source implementation domain/group: `charts/distribution`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.violin_label.ChartsDistributionViolinDistributionFeatureLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.
