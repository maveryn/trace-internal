# `task_charts__sankey__source_to_target_total_flow`

## Contract
1. Domain: `charts`
2. Scene id: `sankey`
3. Task id: `task_charts__sankey__source_to_target_total_flow`
4. Objective contract: `source_to_target_total_flow`
5. Supported `query_id` values: `single`

## Program Contract
`sum(min(value(source_to_middle), value(middle_to_target)) for route in routes(source_label, target_label)); scene=sankey; scope=source_to_target_total_flow`

## Implementation
1. Registered class: `trace.tasks.charts.sankey.source_to_target_total_flow.ChartsFlowSankeySourceToTargetTotalFlowPublicTask`
2. Prompt bundle: `charts_sankey_v1`
3. Scene key: `sankey`
4. Task key: `sankey_path_query`
5. Query key: `source_to_target_total_flow`

## Annotation Contract
1. Answer schema: `integer_value`
2. Annotation schema: `bbox_set`
3. Annotation marks the printed value-label boxes for the two Sankey bands on every route included in the sum.
4. Node boxes, unselected flow labels, flow curves, title, and panel frame are context unless explicitly referenced by the task.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `source_label,target_label` | `integer_value` | `bbox_set` |
