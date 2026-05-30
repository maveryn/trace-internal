# `task_charts__radial_sankey__dominant_endpoint_label`

## Contract
1. Domain: `charts`
2. Scene id: `radial_sankey`
3. Source implementation domain/group: `charts/flow`
4. Query id: `largest_source_for_target`, `largest_target_for_source`, `second_largest_target_for_source`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.flow.radial_sankey.ChartsFlowRadialSankeyDominantEndpointLabelPublicTask`
2. Prompt lookup domain/group: `charts/flow`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence
1. Evidence type: `bbox_set`.
2. Boxes mark the printed flow-value labels being compared and the selected endpoint node box.
