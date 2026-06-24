# `task_three_d__conveyor_sorting__scoped_segment_object_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor_sorting`
- Scene package: `conveyor_sorting`
- Query ids: `object_type_segment_count`, `color_segment_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, lane_label=target_lane_label, segment_key=target_segment_key, target_attribute_match=true)); scene=conveyor_sorting; scope=scoped_segment_object_count`

## Contract
The image shows one conveyor sorting station with one to three lanes. Each lane
has visible labeled belt segments: `INPUT`, `SCAN`, and `OUTPUT`. Small 3D
objects sit in slot-like positions on the belt surfaces.

For `object_type_segment_count`, the task asks for the number of objects of one
sampled object type in the requested lane segment. For `color_segment_count`,
the task asks for the number of objects with one canonical named color in the
requested lane segment.

The answer is the integer count of finalized objects whose lane, segment, and
target attribute match the query.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted target object. Other objects, belt segments, lane labels, segment
labels, rails, scanner frames, and decorative station context are not
annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_sorting_v1` under
`prompts/three_d/conveyor_sorting/`. Named color prompts use the canonical
repo-wide color format, such as `blue [#2D75E6]`.

The trace records scene variant, lane/segment records, target lane and segment,
target attribute, object specs, projected object boxes and centers, camera,
projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized conveyor trace.
