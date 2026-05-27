# `task_charts__sankey__path_value`

## Contract
1. Domain: `charts`
2. Scene id: `sankey`
3. Source implementation domain/group: `charts/flow`
4. Query id: `path_bottleneck_value`, `path_flow_difference`, `source_to_target_total_flow`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.flow.sankey_path_value.ChartsFlowSankeyPathValuePublicTask`
2. Prompt lookup domain/group: `charts/flow`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
