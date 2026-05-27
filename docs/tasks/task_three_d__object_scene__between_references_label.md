# `task_three_d__object_scene__between_references_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `between_references`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, two unlettered reference props named in the question, and `6` lettered answer candidates.

The prompt asks which lettered object is between the two named reference objects. Generation places exactly one lettered candidate in the floor-plane corridor between the references. The remaining lettered candidates are placed outside that corridor and are constrained away from heavy visual overlap with either reference.

The answer is computed from metadata using each candidate's projected position along the reference-to-reference floor segment, lateral distance from that segment, and endpoint margin. Pixels are render output, not the verifier source of truth.

## Evidence Contract
Evidence is the bounding box of the selected lettered 3D object. The two named reference objects are present in the trace and render map, but they are not part of the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference ids/names/shapes, per-label between metrics, per-label between truth values, and projected object bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.
