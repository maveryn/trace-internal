# `task_three_d__object_cluster__color_membership_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Query id: `color_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows a dense synthetic perspective 3D cluster of colored small objects on a plain surface. The prompt asks how many objects match one semantic color, such as blue objects or red objects.

The answer is the integer count of finalized clustered objects whose recorded `color_name` equals the sampled target color. Semantic color is recorded in verifier metadata as `color_name`, `prompt_color_name`, and `fill_rgb`; pixels are render output, not verifier source of truth.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object matching the requested color. The annotation set is unordered because all witnesses have the same role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v0` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target color, target object ids, per-color counts, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
