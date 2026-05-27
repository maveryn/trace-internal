# `task_three_d__object_scene__object_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `on_top_of_prop|under_prop|inside_prop`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the same open synthetic perspective 3D object scene as the camera-distance task: a gridded floor or platform, small lettered answer-candidate objects, and larger unlettered props. The prompt asks which small lettered object has a spatial relation to a named prop.

The relation branch is recorded in `query_id`. `on_top_of_prop` samples a table, shelf, or stand; `under_prop` samples a bridge, arch, or table; `inside_prop` samples a low open box drawn like a tray so the contained object remains visible. Each instance constructs exactly one matching small lettered object by world-coordinate placement, then places the remaining small lettered objects outside that relation.

The shared scene camera samples front, side, and rear oblique orbit bands, so relation questions are viewed from varied 3D perspectives rather than one fixed side.

Each instance renders `6` small lettered answer candidates and `2` larger context props. The answer remains the visible option letter, not the object name.

For `inside_prop`, the answer candidate is placed on the open-box floor rather than the world floor, the sampled answer shape is restricted to object types whose renderer supports elevated bases, and the contained answer uses a foreground render-order bias so the tray cannot paint over the correct option.

## Evidence Contract
Evidence is the bounding box of the selected small lettered 3D object. The named prop is a reference object in the prompt and trace, but it is not included in the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, object roles, prompt-facing names, the reference prop id/name, per-label relation truth, and projected object bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
