# `task_three_d__conveyor__lane_color_count_arithmetic_value`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Query ids: `total_count`, `difference_count`
- Answer type: `integer`
- Annotation type: `bbox_set_map`

## Program Contract
- `arithmetic(count(filter(conveyor_objects, lane_key=left_lane_key, color_name=target_color_name)), count(filter(conveyor_objects, lane_key=right_lane_key, color_name=target_color_name)), operator=query_id); scene=conveyor; scope=lane_color_count_arithmetic_value`

## Contract
The scene has three straight conveyor lanes. The prompt selects two lanes and one semantic color, then asks for either the total or absolute difference across the two lanes. Color is a sampled operand; arithmetic operator is the query id.

## Annotation Contract
Annotation is a `bbox_set_map` keyed by selected lane roles, such as `top_objects` and `middle_objects`. Each value contains `[x0, y0, x1, y1]` boxes around counted colored objects for that lane.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1`. Trace metadata records `internal_query_id` as `color_count_sum` or `color_count_difference`.
