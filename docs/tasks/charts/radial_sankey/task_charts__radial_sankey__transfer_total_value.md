# `task_charts__radial_sankey__transfer_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `radial_sankey`
3. Task id: `task_charts__radial_sankey__transfer_total_value`
4. Objective contract: `transfer_total_value`
5. Supported `query_id` values: `source_to_targets_total`, `sources_to_target_total`

## Program Contract
`sum(value(flow) for flow in grouped_flows sharing one endpoint); scene=radial_sankey; scope=transfer_total_value`

## Implementation
1. Registered class: `trace.tasks.charts.radial_sankey.transfer_total_value.ChartsRadialSankeyTransferTotalValueTask`
2. Prompt bundle: `charts_radial_sankey_v1`
3. Scene key: `radial_sankey`
4. Task key: `radial_sankey_query`
5. Query keys: `source_to_targets_total`, `sources_to_target_total`

## Annotation Contract
1. Answer schema: `integer_value`
2. Annotation schema: `bbox_set`
3. Annotation marks the printed value-label boxes for every flow included in the sum.
4. Source/target node boxes, unselected flow labels, the flow curves, title, panel frame, and ring are context unless explicitly referenced by the task.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `source_to_targets_total` | `fixed_endpoint=source; grouped_endpoint=targets` | `integer_value` | `bbox_set` |
| `sources_to_target_total` | `fixed_endpoint=target; grouped_endpoint=sources` | `integer_value` | `bbox_set` |
