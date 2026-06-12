# `task_three_d__object_scene__multiview_object_match_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `same_object_in_second_view`
- Answer type: `option_letter`
- Annotation type: role-keyed `keyed_bbox_map`
- Status: pending_v0_review

## Contract
The image shows two side-by-side perspective views of the same finalized synthetic 3D object scene. The left view hides option letters and marks one source object with a red box. The right view shows the same answer-candidate objects with option letters.

The prompt asks which lettered object in the right view is the same physical object as the red-boxed object in the left view. The answer is computed from stable object identity in metadata: the right-view candidate whose `canonical_object_id` matches the red-boxed left-view object. The task does not use pixels as verifier source of truth.

Each instance uses `6` compact lettered candidate objects by default. Larger props are omitted in this first multiview task so candidate visibility stays reliable across both camera projections. Candidate placement and dimensions use a multiview readability profile that keeps objects closer to the panel camera and large enough after projection. Candidate colors and dimensions are fixed per canonical object before both camera projections, so the same object has consistent appearance across views. The two cameras are sampled from separated orbit bands and generation records both camera poses, projection frames, per-view object specs, and yaw separation.

## Annotation Contract
Annotation is a `keyed_bbox_map` with:
- `reference_view_object`: bbox around the red-boxed object in the left/source view.
- `second_view_match`: bbox around the matched lettered object in the right/candidate view.

Keyed annotation is required because the two witness boxes have distinct source-vs-target roles. The red-box annotation itself is render guidance; the verifier uses finalized object metadata and projected object boxes.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records canonical object ids, answer label, target object id/name/shape, both view cameras, both projection frames, per-view projected object boxes, and the candidate-label map used by the verifier.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
