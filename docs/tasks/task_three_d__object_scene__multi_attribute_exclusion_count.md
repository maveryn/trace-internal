# `task_three_d__object_scene__multi_attribute_exclusion_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `object_type_and_not_color_count`, `color_and_not_object_type_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered small 3D objects.

The prompt asks for the count of objects satisfying one visible attribute while excluding another, such as cubes that are not red or red objects that are not cubes. Generation includes excluded-overlap distractors so the task requires applying the negative condition.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. Objects matching the excluded attribute are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records color/type metadata, target predicate spec, per-object exclusion status, target object ids, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
