# `task_three_d__object_cluster__total_object_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Query id: `total_object_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows a dense synthetic perspective 3D cluster of small objects on a
plain surface. This level-0 cluster task asks for the total number of visible
objects in the cluster, without filtering by object type, color, relation, or
region.

Generation uses a homogeneous cluster: all visible objects are countable
instances from one sampled object type. The sampled object type is render
variety metadata only and is not named in the prompt. There are no unrelated
distractor objects in this task.

The answer is the integer count of finalized visible objects with
`is_countable_object = true`. Pixels are render output, not verifier source of
truth.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each
counted object. The annotation set is unordered because all witnesses have the
same semantic role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v0` under `prompts/three_d/object_cluster/`.
The trace records camera pose, projection frame, object world coordinates,
sampled dimensions, primary object type metadata, all counted object ids,
projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized 3D scene trace.
