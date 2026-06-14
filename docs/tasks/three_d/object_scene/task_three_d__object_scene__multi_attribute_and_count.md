# `task_three_d__object_scene__multi_attribute_and_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `object_type_and_color_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered small 3D objects.

The prompt asks for the count of objects satisfying a conjunction of two visible attributes, such as red cubes. Generation includes same-type wrong-color and same-color wrong-type distractors so the task requires binding both attributes. The answer is computed from finalized object metadata.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. Distractors, scene support surfaces, and any non-target objects are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records object types, prompt colors, exact color+shape counts, target predicate spec, target object ids, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
