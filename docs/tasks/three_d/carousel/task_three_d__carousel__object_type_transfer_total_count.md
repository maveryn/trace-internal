# `task_three_d__carousel__object_type_transfer_total_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set_map`

## Program Contract
- `count(filter(carousel_objects, belt_key=destination_belt_key)) + count(filter(carousel_objects, belt_key=source_belt_key, shape_type=target_shape_type)); scene=carousel; scope=object_type_transfer_total_count`

## Annotation Contract
Annotation is a `bbox_set_map` with keys `source_moved_objects` and `destination_existing_objects`, each containing `[x0, y0, x1, y1]` boxes before the move.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1`. Trace metadata records `query_id="single"` and `internal_query_id="object_transfer_total_count"`.
