# `task_three_d__conveyor__scoped_belt_color_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, lane_key=target_lane_key, color_name=target_color_name)); scene=conveyor; scope=scoped_belt_color_count`

## Contract
The scene has three straight conveyor lanes. The prompt selects one lane by position and one canonical named color. Target color is a sampled operand, not a query id.

## Annotation Contract
Annotation is an unordered array of `[x0, y0, x1, y1]` pixel boxes around counted colored objects on the requested belt. Empty arrays are valid for answer `0`.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1`. Trace metadata records `query_id="single"` and `internal_query_id="color_belt_count"`.
