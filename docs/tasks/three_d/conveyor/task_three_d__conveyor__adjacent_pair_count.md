# `task_three_d__conveyor__adjacent_pair_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `color_ordered_pair_count`, `object_ordered_pair_count`
- Answer type: `integer`
- Annotation type: `segment_set`
- Annotation schema: `segment_set`

## Program Contract
- `count(i where lane_sequence[target_lane_key][i].color_name=first_target_color_name and lane_sequence[target_lane_key][i+1].color_name=second_target_color_name); scene=conveyor; scope=adjacent_pair_count`
- `count(i where lane_sequence[target_lane_key][i].shape_type=first_target_shape_type and lane_sequence[target_lane_key][i+1].shape_type=second_target_shape_type); scene=conveyor; scope=adjacent_pair_count`

## Contract
The image shows one straight 3D conveyor scene with three visible parallel
lanes. Landscape canvases use `TOP`, `MIDDLE`, and `BOTTOM` lane positions.
Portrait canvases use `LEFT`, `MIDDLE`, and `RIGHT` lane positions. Square
canvases may use either orientation.

The task selects one lane and asks for the number of immediate ordered
neighbor pairs along that lane. For color queries, the ordered predicate is
`first_color` immediately followed by `second_color`. For object queries, the
ordered predicate is `first_shape_type` immediately followed by
`second_shape_type`. The reverse order is not counted. Non-target lanes are
visual distractors.

Answer support is `0..4`. Each lane contains at most 8 objects for this task.

## Annotation Contract
Annotation is a `segment_set`. Each segment marks one counted adjacent ordered
pair by connecting the center of the first object to the center of the second
object in that pair. Objects that are not part of a counted pair, belt
surfaces, arrows, and decorative context are not annotation.

The public reward treats segment endpoints as unordered for distance matching,
but the execution trace records `target_pair_object_id_pairs` in ordered
first-to-second form.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, lane orientation, selected lane key, ordered
target color or object pair, lane object sequence, target pair object ids,
object specs, projected object boxes and centers, projected pair segments,
camera, projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized conveyor trace.
