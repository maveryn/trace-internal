# `task_three_d__conveyor__lane_count_arithmetic_value`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `color_count_sum`, `color_count_difference`, `object_count_sum`, `object_count_difference`
- Answer type: `integer`
- Annotation type: keyed `bbox_set_map`
- Annotation schema: `bbox_set_map`

## Program Contract
- `sum(count(filter(conveyor_objects, lane_key=first_lane_key, color_name=target_color_name)), count(filter(conveyor_objects, lane_key=second_lane_key, color_name=target_color_name))); scene=conveyor; scope=lane_count_arithmetic_value`
- `abs(count(filter(conveyor_objects, lane_key=first_lane_key, color_name=target_color_name)) - count(filter(conveyor_objects, lane_key=second_lane_key, color_name=target_color_name))); scene=conveyor; scope=lane_count_arithmetic_value`
- `sum(count(filter(conveyor_objects, lane_key=first_lane_key, shape_type=target_shape_type)), count(filter(conveyor_objects, lane_key=second_lane_key, shape_type=target_shape_type))); scene=conveyor; scope=lane_count_arithmetic_value`
- `abs(count(filter(conveyor_objects, lane_key=first_lane_key, shape_type=target_shape_type)) - count(filter(conveyor_objects, lane_key=second_lane_key, shape_type=target_shape_type))); scene=conveyor; scope=lane_count_arithmetic_value`

## Contract
The image shows one straight 3D conveyor scene with three visible parallel
lanes. Landscape canvases use `TOP`, `MIDDLE`, and `BOTTOM` lane positions.
Portrait canvases use `LEFT`, `MIDDLE`, and `RIGHT` lane positions. Square
canvases may use either orientation. The task selects two of the three visible
lanes and asks for either the sum or absolute difference of the two scoped
counts. The third lane is a visual distractor and does not count.

Color query ids count objects with one canonical named color in each selected
lane. Object query ids count objects of one sampled object type in each
selected lane. The task does not combine object type and color in the same
predicate.

Each selected-lane operand count has support `0..6`. Sum answers have support
`1..12`. Difference answers have support `1..5`. Each lane contains at most
8 objects.

## Annotation Contract
Annotation is a `bbox_set_map` with keys matching the selected lane positions,
for example `top_objects` and `bottom_objects`, or `left_objects` and
`middle_objects`. Each key maps to one `[x0, y0, x1, y1]` pixel box per counted
object for that lane. Empty arrays are valid when a selected lane operand count
is zero. Objects outside the two requested lanes, objects that are not part of
the requested color/type predicate, belt surfaces, arrows, and decorative
context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, lane orientation, selected lane keys,
arithmetic operation, operand counts by annotation key, target object ids by
annotation key, object specs, projected object boxes and centers, camera,
projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized conveyor trace.
