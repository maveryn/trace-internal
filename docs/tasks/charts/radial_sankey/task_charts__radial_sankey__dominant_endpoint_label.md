# `task_charts__radial_sankey__dominant_endpoint_label`

## Contract
1. Domain: `charts`
2. Scene id: `radial_sankey`
3. Task id: `task_charts__radial_sankey__dominant_endpoint_label`
4. Objective contract: `dominant_endpoint_label`
5. Supported `query_id` values: `largest_target_for_source`, `largest_source_for_target`

## Program Contract
`argmax_label(endpoint(flow), value(flow), fixed_opposite_endpoint); scene=radial_sankey; scope=dominant_endpoint_label`

## Implementation
1. Registered class: `trace.tasks.charts.radial_sankey.dominant_endpoint_label.ChartsRadialSankeyDominantEndpointLabelTask`
2. Prompt bundle: `charts_radial_sankey_v1`
3. Scene key: `radial_sankey`
4. Task key: `radial_sankey_query`
5. Query keys: `largest_target_for_source`, `largest_source_for_target`

## Annotation Contract
1. Answer schema: `string_label`
2. Annotation schema: `bbox_set_map`
3. Annotation maps `compared_flow_values` to the printed value-label boxes for the compared bands and `answer_endpoint` to the selected source or target node box.
4. The flow curves, title, panel frame, ring, and unrelated nodes are context unless explicitly referenced by the task.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_target_for_source` | `endpoint=target; fixed_opposite_endpoint=source_label` | `string_label` | `bbox_set_map` |
| `largest_source_for_target` | `endpoint=source; fixed_opposite_endpoint=target_label` | `string_label` | `bbox_set_map` |
