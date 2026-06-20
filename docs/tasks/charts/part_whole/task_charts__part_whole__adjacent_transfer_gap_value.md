# `task_charts__part_whole__adjacent_transfer_gap_value`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Supported `query_id`: `clockwise_adjacent_transfer`, `counterclockwise_adjacent_transfer`
4. Answer schema: `integer_value`
5. Annotation schema: `point_map`

## Implementation
1. Registered class: `trace.tasks.charts.part_whole.adjacent_transfer_gap_value.ChartsCompositionChartAdjacentTransferGapValueTask`
2. Prompt lookup domain/scene: `charts/part_whole`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`absolute_difference(value(source_category) - transfer_delta, value(adjacent_category(source_category, direction)) + transfer_delta); scene=part_whole; scope=adjacent_transfer_gap_value`

## Annotation Contract
Annotation maps the source category label and adjacent target category label to `[x,y]` pixel points at the centers of their chart segments.

## Query Details

| Query id | Adjacent direction | Answer schema | Annotation schema |
|---|---|---|---|
| `clockwise_adjacent_transfer` | clockwise | `integer_value` | `point_map` |
| `counterclockwise_adjacent_transfer` | counterclockwise | `integer_value` | `point_map` |
