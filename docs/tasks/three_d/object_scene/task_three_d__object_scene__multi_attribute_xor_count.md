# `task_three_d__object_scene__multi_attribute_xor_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered small 3D objects.

The prompt asks for the count of objects satisfying exactly one of two visible attributes: the target object type or the target color, but not both. Generation includes both-matching objects as explicit distractors so the task differs from inclusive OR.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. Objects satisfying both attributes are excluded from annotation and from the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records color/type metadata, target predicate spec, exact-one status by object, target object ids, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
