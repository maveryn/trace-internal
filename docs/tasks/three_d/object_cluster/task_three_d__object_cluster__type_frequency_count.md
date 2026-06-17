# `task_three_d__object_cluster__type_frequency_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`s: `most_frequent_type_count`, `singleton_type_count`
- Answer type: `integer`
- Annotation type: unordered `point_set`
- Annotation schema: `point_set`

## Program Contract
`count(filter(object_cluster_objects, frequency_rule = selected_frequency_rule)); scene=object_cluster; scope=type_frequency_count`

## Contract
The image shows many small synthetic perspective 3D objects arranged on a plain surface. The prompt asks for a count derived from object-type frequencies: either the count of the unique most frequent object type, or the number of objects whose type appears exactly once.

The answer is the integer count derived from finalized `shape_type` frequencies. Generation enforces a unique most-frequent type for `most_frequent_type_count` and exact singleton membership for `singleton_type_count`.

## Annotation Contract
Annotation is a `point_set` containing one center point for each counted object: all objects in the most frequent type for the most-frequent query, or all singleton-type objects for the singleton query. The annotation set is unordered because all witnesses have the same role.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, target/singleton type metadata, per-shape counts, target object ids, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
