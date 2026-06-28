# `task_three_d__conveyor__scoped_belt_object_type_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, lane_key=target_lane_key, shape_type=target_shape_type)); scene=conveyor; scope=scoped_belt_object_type_count`

## Contract
The scene has three straight conveyor lanes. The prompt selects one lane by position and one object type. Target object type is a sampled operand, not a query id.

## Annotation Contract
Annotation is an unordered array of `[x0, y0, x1, y1]` pixel boxes around counted objects on the requested belt. Empty arrays are valid for answer `0`.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1`. Trace metadata records `query_id="single"` and `internal_query_id="object_type_belt_count"`.
