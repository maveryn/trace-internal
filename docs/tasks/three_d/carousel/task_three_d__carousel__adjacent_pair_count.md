# `task_three_d__carousel__adjacent_pair_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Scene package: `carousel`
- Query ids: `color_ordered_pair_count`, `object_ordered_pair_count`
- Answer type: `integer`
- Annotation type: `segment_set`
- Annotation schema: `segment_set`

## Program Contract
- `count(i where belt_cycle[target_belt_key][i].color_name=first_target_color_name and belt_cycle[target_belt_key][(i+1) mod n].color_name=second_target_color_name); scene=carousel; scope=adjacent_pair_count`
- `count(i where belt_cycle[target_belt_key][i].shape_type=first_target_shape_type and belt_cycle[target_belt_key][(i+1) mod n].shape_type=second_target_shape_type); scene=carousel; scope=adjacent_pair_count`

## Contract
The image shows one 3D conveyor carousel with two visible concentric
elliptical belts: an inner belt and an outer belt. The task selects one belt
and asks for the number of immediate ordered neighbor pairs along the belt's
arrow direction.

For color queries, the ordered predicate is `first_color` immediately followed
by `second_color`. For object queries, the ordered predicate is
`first_shape_type` immediately followed by `second_shape_type`. The reverse
order is not counted. The non-target belt is a visual distractor.

Answer support is `1..5`. Belt sequences are cyclic for the program contract:
the final visible object on the selected belt is adjacent to the first visible
object in belt order.

## Annotation Contract
Annotation is a `segment_set`. Each segment marks one counted adjacent ordered
pair by connecting the center of the first object to the center of the second
object in that pair. Objects that are not part of a counted pair, belt
surfaces, arrows, and decorative context are not annotation.

The public reward treats segment endpoints as unordered for distance matching,
but the execution trace records `target_pair_object_id_pairs` in ordered
first-to-second form.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1` under
`prompts/three_d/carousel/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, selected belt key, ordered target color or
object pair, belt object sequence, target pair object ids, object specs,
projected object boxes and centers, projected pair segments, camera,
projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized carousel trace.
