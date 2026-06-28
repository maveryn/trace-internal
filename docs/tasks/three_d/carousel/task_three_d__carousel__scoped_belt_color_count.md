# `task_three_d__carousel__scoped_belt_color_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set`

## Program Contract
- `count(filter(carousel_objects, belt_key=target_belt_key, color_name=target_color_name)); scene=carousel; scope=scoped_belt_color_count`

## Contract
The scene has inner and outer elliptical conveyor belts. The prompt selects one belt and one canonical named color. Target color is a sampled operand, not a query id.

## Annotation Contract
Annotation is an unordered array of `[x0, y0, x1, y1]` pixel boxes around counted colored objects on the requested belt. Empty arrays are valid for answer `0`.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1`. Trace metadata records `query_id="single"` and `internal_query_id="color_belt_count"`.
