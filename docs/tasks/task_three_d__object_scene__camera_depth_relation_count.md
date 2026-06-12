# `task_three_d__object_scene__camera_depth_relation_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query ids: `closer_to_camera_than_reference_count`, `farther_from_camera_than_reference_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered prompt-name-safe small 3D objects.

The prompt names one unique reference object and asks how many other small objects are closer to or farther from the camera than that reference. The answer is computed from finalized camera-distance metadata with minimum margins around the reference, avoiding ambiguous `in front of` or `behind` wording.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. The named reference object is recorded in trace metadata but excluded from prompt-facing annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. Depth templates must explicitly say `closer/farther from the camera`. The trace records camera pose, reference id/name, per-object camera distance, per-object relation status, target object ids, projected boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
