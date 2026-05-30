# `task_three_d__object_scene__named_object_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `object_type_count`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform and many unlettered small 3D objects. No large context props are used in this task so countable objects are not hidden by furniture-sized distractors.

The prompt asks how many objects of one named object type are present, such as balls, cylinders, books, or helmets. The target object type is sampled from the full object-scene small-object pool. Generation places `13-16` small objects by default, allows repeated target objects, and uses non-target small objects as distractors.

The answer is the integer count of finalized objects whose `shape_type` equals the sampled target shape. Pixels are render output, not verifier source of truth.

## Evidence Contract
Evidence is a `bbox_set` containing one whole-object bounding box for each counted target object. The evidence set is unordered because all witnesses have the same semantic role and evidence cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, target shape, target object ids, per-shape counts, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.
