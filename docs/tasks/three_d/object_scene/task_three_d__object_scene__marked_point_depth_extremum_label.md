# `task_three_d__object_scene__marked_point_depth_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: role-keyed `keyed_point_map`

## Contract
The image shows one synthetic perspective 3D object scene with a full-canvas gridded floor/table/platform, unlettered context objects, and lettered point markers in the scene. The prompt asks which marked point is closest to or farthest from the camera.

The verifier computes the answer from the finalized 3D camera distance of each marked point, not from pixels. The marker labels are assigned after the true extremum point is selected so the answer label distribution remains broad instead of being tied to a fixed layout position.

Each default instance renders six marked points, with a mix of floor points and object-surface points when feasible. The context objects remain unlettered and are not answer candidates.

## Annotation Contract
Annotation is a `keyed_point_map` with:
- `selected_point`: the pixel center of the selected marker letter.

The marker label text, context objects, floor grid, shadows, and background geometry are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records camera pose, projection frame, context object metadata, marked-point world coordinates, projected marker centers, camera distances by point label, and the near-to-far marker-label order used by the verifier.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
