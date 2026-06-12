# `task_three_d__object_cluster__type_union_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Query id: `two_type_union_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a dense synthetic perspective 3D cluster of small objects on a plain surface. The prompt asks how many objects belong to either of two named object types.

The answer is the integer count of finalized clustered objects whose recorded `shape_type` is one of the two sampled target types. The two target type sets are disjoint by construction, so each object is counted at most once.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object whose type belongs to the two-type union. The annotation set is unordered because all witnesses have the same role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v0` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, target type names, target object ids, per-shape counts, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
