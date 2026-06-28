# `task_three_d__carousel__belt_color_count_arithmetic_value`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Query ids: `total_count`, `difference_count`
- Answer type: `integer`
- Annotation type: `bbox_set_map`

## Program Contract
- `arithmetic(count(filter(carousel_objects, belt_key=left_belt_key, color_name=target_color_name)), count(filter(carousel_objects, belt_key=right_belt_key, color_name=target_color_name)), operator=query_id); scene=carousel; scope=belt_color_count_arithmetic_value`

## Contract
The scene has inner and outer carousel belts. The prompt names one semantic color and asks for either the total or absolute difference across the two belts. Color is a sampled operand; arithmetic operator is the query id.

## Annotation Contract
Annotation is a `bbox_set_map` with keys `inner_objects` and `outer_objects`, each containing `[x0, y0, x1, y1]` boxes around counted colored objects for that belt.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1`. Trace metadata records `internal_query_id` as `color_count_sum` or `color_count_difference`.
