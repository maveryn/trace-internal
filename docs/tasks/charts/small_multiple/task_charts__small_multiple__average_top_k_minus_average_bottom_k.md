# `task_charts__small_multiple__average_top_k_minus_average_bottom_k`

## Contract
1. Domain: `charts`
2. Scene id: `small_multiple`
3. Public task id: `task_charts__small_multiple__average_top_k_minus_average_bottom_k`
4. Query id: `single`

## Implementation
1. Registered class: `trace.tasks.charts.small_multiple.average_top_k_minus_average_bottom_k.ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask`
2. Prompt bundle: `charts_small_multiple_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_map`.
3. Annotation marks rank-segment and target-segment labels in the selected top and bottom panels.

## Program Contract
`difference(mean(share(panel,target_segment) for panel in top_k(panels, share(panel,rank_segment), k)), mean(share(panel,target_segment) for panel in bottom_k(panels, share(panel,rank_segment), k))); output=integer_value; annotation=point_map(rank_segment,target_segment for top_bottom_panels); scene=small_multiple; scope=average_top_k_minus_average_bottom_k`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `difference(mean(top_k target shares), mean(bottom_k target shares))` | `integer_value` | `point_map` |
