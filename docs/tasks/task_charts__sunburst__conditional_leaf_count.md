# `task_charts__sunburst__conditional_leaf_count`

## Contract
1. Domain: `charts`
2. Scene id: `sunburst`
3. Source implementation domain/group: `charts/composition`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` over the printed outer leaf value labels checked under the requested parent category.

## Implementation
1. Registered class: `trace.tasks.charts.composition.sunburst_hierarchy.ChartsCompositionSunburstConditionalLeafCountTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
