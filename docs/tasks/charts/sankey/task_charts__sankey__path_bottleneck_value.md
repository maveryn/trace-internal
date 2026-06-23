# `task_charts__sankey__path_bottleneck_value`

## Contract
1. Domain: `charts`
2. Scene id: `sankey`
3. Task id: `task_charts__sankey__path_bottleneck_value`
4. Objective contract: `path_bottleneck_value`
5. Supported `query_id` values: `single`

## Program Contract
`min(value(source_to_middle), value(middle_to_target)); scene=sankey; scope=path_bottleneck_value`

## Implementation
1. Registered class: `trace.tasks.charts.sankey.path_bottleneck_value.ChartsFlowSankeyPathBottleneckValuePublicTask`
2. Prompt bundle: `charts_sankey_v1`
3. Scene key: `sankey`
4. Task key: `sankey_path_query`
5. Query key: `path_bottleneck_value`

## Annotation Contract
1. Answer schema: `integer_value`
2. Annotation schema: `bbox_set`
3. Annotation marks the two printed value-label boxes on the selected source-middle-target path.
4. Node boxes, unselected flow labels, flow curves, title, and panel frame are context unless explicitly referenced by the task.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `selected_path` | `integer_value` | `bbox_set` |
