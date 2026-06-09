# `task_three_d__object_scene__landmark_correspondence_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `landmark_correspondence`
- Answer type: `option_letter`
- Annotation type: role-keyed `keyed_point_map`
- Status: pending_v0_review

## Contract
The image shows two side-by-side perspective views of the same kind of recognizable 3D object. The left view marks one local object landmark with a red `REF` point. The right view shows another object of the same type with four red-circled candidate landmark points labeled `A` through `D`.

The prompt asks which right-view candidate point corresponds to the marked left-view landmark. The answer is computed from the landmark id recorded in metadata, not from pixels. The initial supported shape pool is intentionally restricted to asymmetric or feature-rich objects: `fish`, `key`, `hammer`, `sword`, `glove`, `leaf`, `plug`, and `open_book`.

Each instance samples object scale, position, color metadata, scene variant, and two separated camera views. Generation rejects samples where the object is too small, the marked points are too close together, or candidate markers would fall near the panel edge.

## Annotation Contract
Annotation is a `keyed_point_map` with:
- `reference_landmark`: pixel point at the red `REF` marker in the left/source view.
- `matched_landmark`: pixel point at the corresponding candidate marker in the right/candidate view.

Keyed point annotation is required because the two points have distinct source-vs-target roles. Option labels localize candidate points in the second view and are not themselves answer annotation.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records the shape type/name, target landmark id/name, answer label, label-to-landmark map, both object specs, both view cameras, both projection frames, marker points, marker boxes, and the keyed annotation points used by the verifier.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
