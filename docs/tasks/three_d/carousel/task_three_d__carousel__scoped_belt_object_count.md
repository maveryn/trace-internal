# `task_three_d__carousel__scoped_belt_object_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Scene package: `carousel`
- Query ids: `object_type_belt_count`, `color_belt_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, belt_key=target_belt_key, target_attribute_match=true)); scene=carousel; scope=scoped_belt_object_count`

## Contract
The image shows one 3D airport-style conveyor carousel with two visible
concentric elliptical belts: an inner belt and an outer belt. The belts are
distinguished by position, not by text written on the image. Small 3D objects
sit on the belt surfaces. For this scoped-count task, the inner belt contains
at most 8 objects and the outer belt contains at most 12 objects.

For `object_type_belt_count`, the task asks for the number of objects of one
sampled object type on the requested belt. For `color_belt_count`, the task asks
for the number of objects with one canonical named color on the requested belt.

The answer is the integer count of finalized objects whose belt and target
attribute match the query. The answer support is `0..5`. Object-type queries
include same-belt objects of other types as distractors. Color queries include
same-belt objects of other canonical named colors as distractors.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted target object. Other objects, belt surfaces, arrows, and
decorative station context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1` under
`prompts/three_d/carousel/`. Named color prompts use the canonical
repo-wide color format, such as `blue [#2D75E6]`.

The trace records scene variant, belt records, target belt, target attribute,
object specs, projected object boxes and centers, camera, projection frame, and
solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized conveyor trace.
