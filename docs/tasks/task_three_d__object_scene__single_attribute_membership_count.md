# `task_three_d__object_scene__single_attribute_membership_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query ids: `object_type_count`, `object_type_union_count`, `color_union_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with many unlettered small 3D objects on a floor, tabletop, or platform surface.

The prompt asks for the count of objects satisfying one visible attribute-membership predicate: one object type, either of two object types, or either of two prompt colors. Generation uses the color-safe object-scene small-shape pool for this task so color remains readable when it is semantic. The answer is computed from finalized object metadata, not pixels.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted object. The annotation set is unordered because all witnesses have the same role and annotation cardinality equals the integer answer.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, object types, prompt colors, target predicate spec, target object ids, projected object boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
