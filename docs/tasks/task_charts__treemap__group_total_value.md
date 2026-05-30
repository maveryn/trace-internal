# `task_charts__treemap__group_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `treemap`
3. Source implementation domain/group: `charts/composition`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` over printed child value labels inside the requested parent rectangle.

## Implementation
1. Registered class: `trace.tasks.charts.composition.treemap_composition.ChartsCompositionTreemapGroupTotalValueTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
