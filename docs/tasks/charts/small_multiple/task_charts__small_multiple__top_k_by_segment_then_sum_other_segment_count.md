# `task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count`

## Contract
1. Domain: `charts`
2. Scene id: `small_multiple`
3. Public task id: `task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count`
4. Query id: `single`

## Implementation
1. Registered class: `trace.tasks.charts.small_multiple.top_k_by_segment_then_sum_other_segment_count.ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask`
2. Prompt bundle: `charts_small_multiple_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_map`.
3. Annotation marks the selected panels' ranking segment labels, target segment labels, and total-count text.

## Program Contract
`sum(count(panel,target_segment) for panel in top_k(panels, share(panel,rank_segment), k)); output=integer_count; annotation=point_map(rank_segment,target_segment,total for selected_panels); scene=small_multiple; scope=top_k_by_segment_then_sum_other_segment_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `sum(count(panel,target_segment) for panel in top_k(panels, share(panel,rank_segment), k))` | `integer_count` | `point_map` |
