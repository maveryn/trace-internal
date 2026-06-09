# `task_three_d__object_scene__image_plane_lateral_relation_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `left_of_reference_in_view_count`, `right_of_reference_in_view_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered prompt-name-safe small 3D objects.

The prompt names one unique reference object and asks how many other small objects appear to its left or right in the final image. Left/right is explicitly image-plane relative, not world-axis relative and not the reference object's own left/right. The answer is computed from finalized projected screen-center x coordinates with minimum margins around the reference.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. The named reference object is recorded in trace metadata but excluded from prompt-facing annotation.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. Left/right templates must include `in the image` or equivalent image-plane wording. The trace records camera pose, projected centers, reference id/name, per-object relation status, target object ids, projected boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
