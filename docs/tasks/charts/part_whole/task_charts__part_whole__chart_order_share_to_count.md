# `task_charts__part_whole__chart_order_share_to_count`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Supported `query_id`: `clockwise_share_to_count`, `counterclockwise_share_to_count`
4. Answer schema: `integer_count`
5. Annotation schema: `point_map`

## Implementation
1. Registered class: `trace.tasks.charts.part_whole.chart_order_share_to_count.ChartsCompositionChartOrderShareToCountTask`
2. Prompt lookup domain/scene: `charts/part_whole`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`count_from_percent(total_count, sum(value(category) for category in contiguous_circular_span(start_category, end_category, direction))); scene=part_whole; scope=chart_order_share_to_count`

## Annotation Contract
Annotation maps each included category label to the `[x,y]` pixel point at the center of its chart segment and maps `total_count` to the `[x,y]` point on the displayed total-count text.

## Query Details

| Query id | Direction | Answer schema | Annotation schema |
|---|---|---|---|
| `clockwise_share_to_count` | clockwise | `integer_count` | `point_map` |
| `counterclockwise_share_to_count` | counterclockwise | `integer_count` | `point_map` |
