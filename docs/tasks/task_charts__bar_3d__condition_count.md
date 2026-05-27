# `task_charts__bar_3d__condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation domain/group: `charts/three_d_bar`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.three_d_bar.grid_query.ChartsThreeDBarConditionCountTask`
2. Prompt lookup domain/group: `charts/three_d_bar`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
