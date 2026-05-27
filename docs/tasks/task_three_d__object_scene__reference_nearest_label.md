# `task_three_d__object_scene__reference_nearest_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `closest_to_reference`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed pending probe

## Contract
The image shows the same open synthetic perspective 3D object scene as the other `three_d/spatial` tasks: a gridded floor or platform, perspective camera cues, and 3D objects with explicit world coordinates and projected boxes.

Each instance renders one unlettered reference object named in the question plus `6` lettered answer candidates. The prompt asks which lettered 3D object is closest to that reference. The reference object is excluded from the answer options by construction.

Candidate objects may include both compact solids and larger prop-scale objects. The default mix uses `2` large lettered candidates and `4` small lettered candidates. The named reference may also be a small or large nameable object, but its prompt-facing name is unique within the scene so the reference is unambiguous.

The answer is computed from metadata using the nearest ground-plane surface gap between the reference object and each lettered candidate. Generation enforces a unique closest candidate and records the full nearest-order list plus the winning margin.

## Evidence Contract
Evidence is the bounding box of the selected lettered 3D object. The named reference object is present in the trace and render map, but it is not part of the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference id/name/shape, per-label surface gaps to the reference, nearest-order labels, and projected object bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
