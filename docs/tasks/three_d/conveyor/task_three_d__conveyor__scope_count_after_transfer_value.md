# `task_three_d__conveyor__scope_count_after_transfer_value`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `color_transfer_total_count`, `object_transfer_total_count`
- Answer type: `integer`
- Annotation type: keyed `bbox_set_map`
- Annotation schema: `bbox_set_map`

## Program Contract
- `count(filter(conveyor_objects, lane_key=destination_lane_key)) + count(filter(conveyor_objects, lane_key=source_lane_key, color_name=target_color_name)); scene=conveyor; scope=scope_count_after_transfer_value`
- `count(filter(conveyor_objects, lane_key=destination_lane_key)) + count(filter(conveyor_objects, lane_key=source_lane_key, shape_type=target_shape_type)); scene=conveyor; scope=scope_count_after_transfer_value`

## Contract
The image shows one straight 3D conveyor scene with three visible parallel
lanes. The task selects a source lane and a distinct destination lane. It asks
for the destination lane's total object count after all source-lane objects
matching one predicate are moved to the destination lane.

Color query ids move all objects of one canonical named color from the source
lane. Object query ids move all objects of one sampled object type from the
source lane. Objects on the third lane are distractors. Matching objects on
non-source lanes are distractors and are not moved.

Moved-object support is `1..4`. The original destination lane contains
`1..8` objects. Final answer support is `2..12`.

## Annotation Contract
Annotation is a `bbox_set_map` with keys `source_moved_objects` and
`destination_existing_objects`. `source_moved_objects` contains one
`[x0, y0, x1, y1]` pixel box for each source-lane object that would be moved.
`destination_existing_objects` contains one box for each object already on the
destination lane before the move. Non-moved source objects, third-lane objects,
belt surfaces, arrows, and decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, lane orientation, source and destination lane
keys, transfer operation, moved count, destination existing count, target
object ids by annotation key, object specs, projected object boxes and centers,
camera, projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized conveyor trace.
