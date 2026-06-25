# `task_three_d__conveyor_sorting__scoped_belt_object_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor_sorting`
- Scene package: `conveyor_sorting`
- Query ids: `object_type_belt_count`, `color_belt_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, belt_key=target_belt_key, target_attribute_match=true)); scene=conveyor_sorting; scope=scoped_belt_object_count`

## Contract
The image shows one 3D airport-style conveyor carousel with two visible
concentric elliptical belts labeled `INNER` and `OUTER`. Small 3D objects sit on
the belt surfaces.

For `object_type_belt_count`, the task asks for the number of objects of one
sampled object type on the requested belt. For `color_belt_count`, the task asks
for the number of objects with one canonical named color on the requested belt.

The answer is the integer count of finalized objects whose belt and target
attribute match the query.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted target object. Other objects, belt labels, belt surfaces, arrows,
inspection gates, and decorative station context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_sorting_v1` under
`prompts/three_d/conveyor_sorting/`. Named color prompts use the canonical
repo-wide color format, such as `blue [#2D75E6]`.

The trace records scene variant, belt records, target belt, target attribute,
object specs, projected object boxes and centers, camera, projection frame, and
solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized conveyor trace.
