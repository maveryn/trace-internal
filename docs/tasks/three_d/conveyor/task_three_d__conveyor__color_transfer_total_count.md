# `task_three_d__conveyor__color_transfer_total_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Query ids: `single`
- Answer type: `integer`
- Annotation type: `bbox_set_map`

## Program Contract
- `count(filter(conveyor_objects, lane_key=destination_lane_key)) + count(filter(conveyor_objects, lane_key=source_lane_key, color_name=target_color_name)); scene=conveyor; scope=color_transfer_total_count`

## Annotation Contract
Annotation is a `bbox_set_map` with keys `source_moved_objects` and `destination_existing_objects`, each containing `[x0, y0, x1, y1]` boxes before the move.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1`. Trace metadata records `query_id="single"` and `internal_query_id="color_transfer_total_count"`.
