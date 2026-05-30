# `task_three_d__object_scene__view_relation_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `left_of_reference_in_view_count`, `right_of_reference_in_view_count`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform and many unlettered, prompt-name-safe small 3D objects.

The prompt names one unique small reference object and asks how many other small objects appear to the left or right of it in the image. The reference is identified by object name only; no red box or option letter is drawn on it.

The task is explicitly image-view relative. `left` and `right` mean projected position in the final rendered image, not the reference object's own left side, a world-axis direction, or a wall/lane coordinate.

Generation uses unique prompt-facing object names in each scene so the named reference is unambiguous. The answer is computed from finalized projection metadata: each object's projected screen center, the named reference object's projected screen center, and a minimum horizontal margin around the reference to reject borderline cases.

## Evidence Contract
Evidence is a `bbox_set` containing one whole-object bounding box for each counted small object. The named reference object is recorded in trace metadata but excluded from prompt-facing evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. Query templates must include `in the image` to disambiguate the frame of reference.

The trace records camera pose, projection frame, reference object id/name/shape, reference prompt-name count, per-object world coordinates, projected centers, per-object view-relation truth values, target object ids, projected boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
