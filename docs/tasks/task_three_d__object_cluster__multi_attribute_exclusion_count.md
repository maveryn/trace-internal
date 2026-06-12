# `task_three_d__object_cluster__multi_attribute_exclusion_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Query ids: `type_and_not_color_count`, `color_and_not_type_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a dense synthetic perspective 3D cluster of colored small objects on a plain surface. The prompt asks for a count under one positive attribute while excluding a second attribute: either named type but not named color, or named color but not named type.

The answer is the integer count of finalized clustered objects satisfying the requested exclusion predicate. Generation includes structured excluded-overlap distractors, such as red buttons when the prompt asks for buttons that are not red.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object satisfying the requested exclusion predicate. The annotation set is unordered because all witnesses have the same role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v0` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target type/color, target object ids, shape/color/property counts, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
