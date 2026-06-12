# `task_three_d__object_scene__marked_point_vertical_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `directly_above_reference`
- Answer type: `option_letter`
- Annotation type: role-keyed `keyed_point_map`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform, uniquely named unlettered small 3D objects, and six lettered point markers `A-F`.

The prompt names one unique small reference object and asks which lettered point is directly above that object in 3D space. The reference object is chosen from a restricted stable-reference small-object pool where a vertical center/top relation is visually meaningful. Other scene objects may use the full prompt-name-safe small-object pool.

The relation is world-vertical, not screen-relative. The answer marker has the same floor-plane `x/y` center as the reference object and a greater `z` coordinate above the reference. Distractor markers are offset from the reference in floor-plane coordinates by a recorded minimum margin.

## Annotation Contract
Annotation is a `keyed_point_map` with key `selected_point`; the value is the pixel point at the center of the selected marker letter. The reference object id, name, projected bbox, and center are recorded in trace/render metadata but are not prompt-facing annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. Query templates must say `directly above`, `vertically above`, or equivalent wording and include the named reference object.

The trace records camera pose, projection frame, reference object id/name/shape, reference prompt-name count, per-object world coordinates and projected bboxes, per-marker world coordinates, projected marker centers, the answer marker id/label, and per-label floor-plane offsets from the reference object.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
