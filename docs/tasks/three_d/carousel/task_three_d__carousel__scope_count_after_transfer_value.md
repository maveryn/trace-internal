# `task_three_d__carousel__scope_count_after_transfer_value`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Scene package: `carousel`
- Query ids: `color_transfer_total_count`, `object_transfer_total_count`
- Answer type: `integer`
- Annotation type: keyed `bbox_set_map`
- Annotation schema: `bbox_set_map`

## Program Contract
- `count(filter(conveyor_objects, belt_key=destination_belt_key)) + count(filter(conveyor_objects, belt_key=source_belt_key, color_name=target_color_name)); scene=carousel; scope=scope_count_after_transfer_value`
- `count(filter(conveyor_objects, belt_key=destination_belt_key)) + count(filter(conveyor_objects, belt_key=source_belt_key, shape_type=target_shape_type)); scene=carousel; scope=scope_count_after_transfer_value`

## Contract
The image shows one 3D conveyor carousel with two visible concentric
elliptical belts: an inner belt and an outer belt. The task selects one source
belt and the other destination belt. It asks for the destination belt's total
object count after all source-belt objects matching one predicate are moved to
the destination belt.

Color query ids move all objects of one canonical named color from the source
belt. Object query ids move all objects of one sampled object type from the
source belt. Matching objects already on the destination belt are counted only
as part of the destination's existing total; they are not moved.

Moved-object support is `1..4`. The final answer is capped by the destination
belt capacity: at most `8` when the destination is `INNER`, and at most `12`
when the destination is `OUTER`.

## Annotation Contract
Annotation is a `bbox_set_map` with keys `source_moved_objects` and
`destination_existing_objects`. `source_moved_objects` contains one
`[x0, y0, x1, y1]` pixel box for each source-belt object that would be moved.
`destination_existing_objects` contains one box for each object already on the
destination belt before the move. Non-moved source objects, belt surfaces,
arrows, and decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1` under
`prompts/three_d/carousel/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, source and destination belt keys, transfer
operation, moved count, destination existing count, target object ids by
annotation key, object specs, projected object boxes and centers, camera,
projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized carousel trace.
