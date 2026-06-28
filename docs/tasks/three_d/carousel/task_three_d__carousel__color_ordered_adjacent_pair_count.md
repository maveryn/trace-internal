# `task_three_d__carousel__color_ordered_adjacent_pair_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `segment_set`

## Program Contract
- `count(ordered_adjacent_pairs(filter(carousel_objects, belt_key=target_belt_key), first_color_name=left_color_name, second_color_name=right_color_name)); scene=carousel; scope=color_ordered_adjacent_pair_count`

## Annotation Contract
Annotation is an array of segments `[[x0, y0], [x1, y1]]`, one per counted ordered pair, from the first object center to the second object center.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1`. Trace metadata records `query_id="single"` and `internal_query_id="color_ordered_pair_count"`.
