# `task_charts__single_series__counterfactual_value`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/hypothetical`
4. Query id: `baseline_from_aggregate_percent_change`, `remaining_mean_after_removal`, `target_share_after_removal`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.hypothetical.counterfactual_value.ChartsHypotheticalCounterfactualValuePublicTask`
2. Prompt lookup domain/group: `charts/hypothetical`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
