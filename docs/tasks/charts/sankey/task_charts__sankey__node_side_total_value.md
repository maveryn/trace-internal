# `task_charts__sankey__node_side_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `sankey`
3. Task id: `task_charts__sankey__node_side_total_value`
4. Objective contract: `node_side_total_value`
5. Supported `query_id` values: `source_outgoing_total_flow`, `target_incoming_total_flow`

## Program Contract
`sum(value(link) for link in node_side_links(node, side)); scene=sankey; scope=node_side_total_value`

## Implementation
1. Registered class: `trace.tasks.charts.sankey.node_side_total_value.ChartsFlowSankeyNodeSideTotalValuePublicTask`
2. Prompt bundle: `charts_sankey_v1`
3. Scene key: `sankey`
4. Task key: `sankey_path_query`
5. Query keys: `source_outgoing_total_flow`, `target_incoming_total_flow`

## Annotation Contract
1. Answer schema: `integer_value`
2. Annotation schema: `bbox_set`
3. Annotation marks multiple printed value-label boxes: every outgoing or incoming band included in the node-side total contributes one box.
4. Node boxes, unselected flow labels, flow curves, title, and panel frame are context unless explicitly referenced by the task.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `source_outgoing_total_flow` | `side=source_outgoing` | `integer_value` | `bbox_set` |
| `target_incoming_total_flow` | `side=target_incoming` | `integer_value` | `bbox_set` |
