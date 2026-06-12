# `task_three_d__object_scene__multi_attribute_or_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `object_type_or_color_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered small 3D objects.

The prompt asks for the count of objects satisfying an inclusive OR over object type and color, such as objects that are cubes or red. Objects satisfying both attributes are counted once. Generation includes objects matching type only, color only, both, and neither so the inclusive-OR contract is visually grounded.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. Annotation cardinality equals the integer answer.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records color/type metadata, target predicate spec, per-object predicate status, target object ids, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
