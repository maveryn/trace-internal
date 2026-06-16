# `task_three_d__object_cluster__multi_attribute_or_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: unordered `point_set`

## Program Contract
`count(unique(filter(object_cluster_objects, shape_type = target_shape_type) union filter(object_cluster_objects, color_name = target_color_name))); scene=object_cluster; scope=multi_attribute_or_count`

## Contract
The image shows a dense synthetic perspective 3D cluster of colored small objects on a plain surface. The prompt asks how many objects match an inclusive OR predicate: the object is the named type or the object has the named color. Prompt-facing semantic colors include the canonical color hex label, for example `red [#E63232]`. Objects matching both conditions are counted once.

The answer is the integer count of finalized clustered objects whose recorded `shape_type` equals the sampled target type or whose `color_name` equals the sampled target color. Generated color distractors avoid near-color named pairs such as blue/cyan/purple and red/maroon/magenta.

## Annotation Contract
Annotation is a `point_set` containing one center point for each counted object satisfying at least one predicate condition. The annotation set is unordered because all counted witnesses have the same role and overlap objects are not duplicated.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target type/color, target object ids, shape/color/property counts, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
