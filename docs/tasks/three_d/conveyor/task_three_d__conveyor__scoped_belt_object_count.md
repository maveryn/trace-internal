# `task_three_d__conveyor__scoped_belt_object_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `object_type_belt_count`, `color_belt_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, lane_key=target_lane_key, target_attribute_match=true)); scene=conveyor; scope=scoped_belt_object_count`

## Contract
The image shows one 3D straight-conveyor scene with three visible parallel
belts. Landscape canvases use three horizontal lanes labeled by prompt position
as `TOP`, `MIDDLE`, or `BOTTOM`. Portrait canvases use three vertical lanes
labeled by prompt position as `LEFT`, `MIDDLE`, or `RIGHT`. Square canvases may
use either orientation. The lane positions are not written as text on the image.

For this scoped-count task, each lane contains at most 8 objects. The target
answer support is `0..5`.

For `object_type_belt_count`, the task asks for the number of objects of one
sampled object type on the requested belt. Same-belt objects of other types are
included as distractors. For `color_belt_count`, the task asks for the number
of objects with one canonical named color on the requested belt. Same-belt
objects of other non-confusable canonical named colors are included as
distractors. Color-readout generation avoids target-confusable named color
distractors, such as red with maroon or blue with cyan.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted target object. Objects on other lanes, same-lane distractor
objects, and belt surfaces are not annotation. If the answer is `0`, the
annotation is an empty `bbox_set`.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, layout orientation, lane records, target lane,
target attribute, object specs, projected object boxes and centers, camera,
projection frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized straight conveyor trace.
