# `task_three_d__object_scene__occlusion_order_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `in_front_of_reference`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: accepted

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, one unlettered reference prop named in the question, and `6` lettered answer candidates. The reference prop is sampled from visually nameable occlusion targets such as an arch, bridge, table, shelf, or stand; open boxes are excluded here to avoid confusing "in front of" with the separate inside-container relation task.

The prompt asks which lettered object appears in front of the named reference object. Generation places exactly one lettered candidate so that it visibly overlaps the reference in the camera view and is closer to the camera. The remaining lettered candidates are placed so they do not meaningfully overlap the reference.

The answer is computed from metadata using projected object overlap and camera distance, not from pixels. The trace records overlap area and depth margin for every candidate label.

## Evidence Contract
Evidence is the bounding box of the selected lettered 3D object. The named reference object is present in the trace and render map, but it is not part of the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference id/name/shape, per-label overlap areas, per-label depth margins, occlusion truth labels, and projected object bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.

## Calibration
Accepted with qwen25vl7b `100x24` calibration on seed `20260521`: hard `0.100`, easy `0.030`, band `0.870`, mean solve `0.310`, response cap `0.000`, prompt max `129`.
