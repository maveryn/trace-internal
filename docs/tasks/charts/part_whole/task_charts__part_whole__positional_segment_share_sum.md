# `task_charts__part_whole__positional_segment_share_sum`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Supported `query_id`: `clockwise_offset_pair`, `counterclockwise_offset_pair`, `clockwise_opposite_pair`, `counterclockwise_opposite_pair`
4. Answer schema: `integer_value`
5. Annotation schema: `point_map`

## Implementation
1. Registered class: `trace.tasks.charts.part_whole.positional_segment_share_sum.ChartsCompositionChartPositionalSegmentShareSumTask`
2. Prompt lookup domain/scene: `charts/part_whole`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`sum(value(category) for category in circular_position_targets(anchor_category, relation, direction)); scene=part_whole; scope=positional_segment_share_sum`

## Annotation Contract
Annotation maps the anchor category label and each target category label to `[x,y]` pixel points at the centers of their chart segments.

## Query Details

| Query id | Relation | Direction | Answer schema | Annotation schema |
|---|---|---|---|---|
| `clockwise_offset_pair` | two offset segments from anchor | clockwise | `integer_value` | `point_map` |
| `counterclockwise_offset_pair` | two offset segments from anchor | counterclockwise | `integer_value` | `point_map` |
| `clockwise_opposite_pair` | opposite segment plus its neighbor | clockwise | `integer_value` | `point_map` |
| `counterclockwise_opposite_pair` | opposite segment plus its neighbor | counterclockwise | `integer_value` | `point_map` |
