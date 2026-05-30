# `task_three_d__object_scene__spatial_relation_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `on_top_of_reference_count`, `under_reference_count`, `inside_reference_count`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform, one named unlettered reference prop, and many unlettered small 3D objects.

The prompt asks how many small objects satisfy one relation to the named reference prop:
- `on_top_of_reference_count`: count small objects on top of a table or shelf.
- `under_reference_count`: count small objects under a table or arch.
- `inside_reference_count`: count small objects inside an open box.

The reference-prop pool is intentionally narrow. Furniture-sized props such as refrigerators, vending machines, sofas, cabinets, lockers, pianos, barrels, and trash bins are excluded because their support/container relation is visually ambiguous or likely to hide countable objects.

Generation places `10-12` small countable objects by default, with `2-3` true relation matches. No option letters are drawn. The answer is computed from finalized 3D metadata: each countable object's world coordinates, base height, footprint relation to the reference prop, and relation branch. Pixels are render output, not verifier source of truth.

## Evidence Contract
Evidence is a `bbox_set` containing one whole-object bounding box for each counted small object. The reference prop is named in the prompt and recorded in trace metadata, but it is not included in prompt-facing evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, reference prop id/name/shape, per-object world coordinates, relation truth values, target object ids, projected boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
