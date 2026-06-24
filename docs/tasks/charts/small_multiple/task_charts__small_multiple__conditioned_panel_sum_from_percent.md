# `task_charts__small_multiple__conditioned_panel_sum_from_percent`

## Contract
1. Domain: `charts`
2. Scene id: `small_multiple`
3. Public task id: `task_charts__small_multiple__conditioned_panel_sum_from_percent`
4. Query id: `single`

## Implementation
1. Registered class: `trace.tasks.charts.small_multiple.conditioned_panel_sum_from_percent.ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask`
2. Prompt bundle: `charts_small_multiple_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_map`.
3. Annotation marks the selected panels' condition segment labels, target segment labels, and total-count text.

## Program Contract
`sum(count(panel,target_segment) for panel in filter(panels, share(panel,condition_segment) > threshold)); output=integer_value; annotation=point_map(condition_segment,target_segment,total for selected_panels); scene=small_multiple; scope=conditioned_panel_sum_from_percent`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `sum(count(panel,target_segment) for panel in filter(panels, share(panel,condition_segment) > threshold))` | `integer_value` | `point_map` |
