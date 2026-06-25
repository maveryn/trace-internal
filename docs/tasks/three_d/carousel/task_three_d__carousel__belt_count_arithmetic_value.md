# `task_three_d__carousel__belt_count_arithmetic_value`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Scene package: `carousel`
- Query ids: `color_count_sum`, `color_count_difference`, `object_count_sum`, `object_count_difference`
- Answer type: `integer`
- Annotation type: keyed `bbox_set_map`
- Annotation schema: `bbox_set_map`

## Program Contract
- `sum(count(filter(conveyor_objects, belt_key=inner, color_name=target_color_name)), count(filter(conveyor_objects, belt_key=outer, color_name=target_color_name))); scene=carousel; scope=belt_count_arithmetic_value`
- `abs(count(filter(conveyor_objects, belt_key=inner, color_name=target_color_name)) - count(filter(conveyor_objects, belt_key=outer, color_name=target_color_name))); scene=carousel; scope=belt_count_arithmetic_value`
- `sum(count(filter(conveyor_objects, belt_key=inner, shape_type=target_shape_type)), count(filter(conveyor_objects, belt_key=outer, shape_type=target_shape_type))); scene=carousel; scope=belt_count_arithmetic_value`
- `abs(count(filter(conveyor_objects, belt_key=inner, shape_type=target_shape_type)) - count(filter(conveyor_objects, belt_key=outer, shape_type=target_shape_type))); scene=carousel; scope=belt_count_arithmetic_value`

## Contract
The image shows one 3D conveyor carousel with two visible concentric
elliptical belts: an inner belt and an outer belt. The task asks for either
the sum or absolute difference of two scoped counts, one from the inner belt
and one from the outer belt.

Color query ids count objects with one canonical named color on each belt.
Object query ids count objects of one sampled object type on each belt. The
task does not combine object type and color in the same predicate.

Each per-belt operand count has support `0..6`. Sum answers have support
`1..12`. Difference answers have support `1..5`. The inner belt contains at
most 8 objects and the outer belt contains at most 12 objects.

## Annotation Contract
Annotation is a `bbox_set_map` with keys `inner_objects` and `outer_objects`.
Each key maps to one `[x0, y0, x1, y1]` pixel box per counted object for that
belt. Empty arrays are valid when a belt operand count is zero. Objects that
are not part of the requested color/type predicate, belt surfaces, arrows, and
decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1` under
`prompts/three_d/carousel/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, belt records, arithmetic operation, operand
counts by annotation key, target object ids by annotation key, object specs,
projected object boxes and centers, camera, projection frame, and solver count
predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized carousel trace.
