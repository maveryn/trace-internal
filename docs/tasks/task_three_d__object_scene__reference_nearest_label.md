# `task_three_d__object_scene__reference_nearest_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `closest_to_reference`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the same open synthetic perspective 3D object scene as the other `three_d/spatial` tasks: a gridded floor or platform, perspective camera cues, unlettered candidate objects, a below-scene text option panel, and 3D objects with explicit world coordinates and projected boxes.

Each instance renders one unlettered reference object named in the question plus `6` unlettered answer candidates described in the option panel. The prompt asks which option describes the 3D object closest to that reference. The reference object is excluded from the answer options by construction.

Candidate objects may include both compact solids and larger prop-scale objects. The default mix uses `2` large candidates and `4` small candidates. The named reference may also be a small or large nameable object, but its prompt-facing name is unique within the scene so the reference is unambiguous.

The answer is computed from metadata using the nearest ground-plane surface gap between the reference object and each candidate. Generation enforces a unique closest candidate and records the full nearest-order list plus the winning margin.

## Annotation Contract
Annotation is the bounding box of the selected 3D object in the scene. The named reference object is present in the trace and render map, but it is not part of the answer annotation; neither the option panel nor option text is annotation.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference id/name/shape, per-label surface gaps to the reference, nearest-order labels, projected object bboxes, and option-panel descriptors/bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
