# `task_charts__part_whole__sector_share_to_angle`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Supported `query_id`: `clockwise_sector_angle`, `counterclockwise_sector_angle`
4. Answer schema: `integer_value`
5. Annotation schema: `point_map`

## Implementation
1. Registered class: `trace.tasks.charts.part_whole.sector_share_to_angle.ChartsCompositionChartSectorShareToAngleTask`
2. Prompt lookup domain/scene: `charts/part_whole`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`degrees(sum(value(category) for category in contiguous_circular_span(start_category, end_category, direction))); scene=part_whole; scope=sector_share_to_angle`

## Annotation Contract
Annotation maps each included category label to the `[x,y]` pixel point at the center of its chart segment.

## Query Details

| Query id | Direction | Answer schema | Annotation schema |
|---|---|---|---|
| `clockwise_sector_angle` | clockwise | `integer_value` | `point_map` |
| `counterclockwise_sector_angle` | counterclockwise | `integer_value` | `point_map` |
