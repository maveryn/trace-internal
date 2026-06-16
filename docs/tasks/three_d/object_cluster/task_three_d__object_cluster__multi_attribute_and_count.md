# `task_three_d__object_cluster__multi_attribute_and_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: unordered `point_set`

## Program Contract
`count(filter(object_cluster_objects, shape_type = target_shape_type and color_name = target_color_name)); scene=object_cluster; scope=multi_attribute_and_count`

## Contract
The image shows a dense synthetic perspective 3D cluster of colored small objects on a plain surface. The prompt asks how many objects match both a named object type and a semantic color, such as red cubes or blue puzzle pieces. Prompt-facing semantic colors include the canonical color hex label, for example `red [#E63232]`, while verifier metadata keeps the raw color name.

This task is distinct from `task_three_d__object_cluster__single_attribute_membership_count`, which counts one object type regardless of color. Generation includes structured partial-match distractors: target-type objects in other colors, target-color objects of other types, and unrelated distractors.

The answer is the integer count of finalized objects whose `shape_type` and `color_name` both match the sampled target predicate. Generated color distractors avoid near-color named pairs such as blue/cyan/purple and red/maroon/magenta. Pixels are render output, not verifier source of truth.

## Annotation Contract
Annotation is a `point_set` containing one center point for each counted object matching both the requested type and color. The annotation set is unordered because all witnesses have the same role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target type/color, target object ids, per-shape counts, per-color counts, per-property counts, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
