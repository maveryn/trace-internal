# `task_three_d__carousel__between_object_type_anchors_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set`

## Program Contract
- `count(objects_between(anchor_a, anchor_b, filter(carousel_objects, belt_key=target_belt_key), direction=belt_direction)); scene=carousel; scope=between_object_type_anchors_count`

## Annotation Contract
Annotation is an unordered array of `[x0, y0, x1, y1]` pixel boxes around the counted objects between the marked anchors. Anchor objects themselves are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1`. Trace metadata records `query_id="single"` and `internal_query_id="between_object_anchors_count"`.
