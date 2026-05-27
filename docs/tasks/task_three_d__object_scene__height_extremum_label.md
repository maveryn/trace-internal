# `task_three_d__object_scene__height_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `highest_above_floor`, `lowest_above_floor`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed pending probe

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, larger support props, and `6` small lettered answer candidates placed at distinct heights above the floor.

The prompt asks which lettered object is sitting highest or lowest above the floor. Generation constructs exactly one vertical extremum by placing lettered candidates on the floor or on visible support props such as an open box, table, bridge, stand, and shelf. The answer is computed from each candidate object's metadata `base_xyz[2]` height above the floor, not from pixel position.

## Evidence Contract
Evidence is the bounding box of the selected lettered 3D object. Larger support props are present in the trace and render map, but they are not part of the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, support object ids, per-label vertical base heights, and the low-to-high height order.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
