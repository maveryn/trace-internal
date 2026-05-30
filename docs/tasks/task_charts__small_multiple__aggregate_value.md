# `task_charts__small_multiple__aggregate_value`

## Contract
1. Domain: `charts`
2. Scene id: `small_multiple`
3. Source implementation domain/group: `charts/composition`
4. Query id: `conditioned_panel_sum_from_percent`, `top_k_by_segment_then_sum_other_segment_count`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_point_map` over the rank/condition, target, and total labels needed for the selected panels.

## Implementation
1. Registered class: `trace.tasks.charts.composition.small_multiples_aggregate_value.ChartsCompositionSmallMultiplesAggregateValuePublicTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
