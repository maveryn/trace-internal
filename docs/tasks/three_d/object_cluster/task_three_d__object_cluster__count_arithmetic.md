# `task_three_d__object_cluster__count_arithmetic`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`s: `two_type_total_count`, `two_type_difference_count`, `two_color_total_count`, `two_color_difference_count`
- Answer type: `integer`
- Annotation type: `keyed_bbox_set_map`
- Annotation schema: `keyed_bbox_set_map`

## Program Contract
`operation(count(filter(object_cluster_objects, operand = left_operand)), count(filter(object_cluster_objects, operand = right_operand))); scene=object_cluster; scope=count_arithmetic`

## Contract
The image shows many small synthetic perspective 3D colored objects arranged on a plain surface. The prompt names two disjoint operand groups, either two object types or two colors, and asks for their total count or the absolute difference between their counts. Prompt-facing semantic colors include the canonical color hex label, for example `blue [#2D75E6]`.

The answer is the requested integer total or absolute count difference. Operand membership is derived from finalized metadata, not pixels. Generated two-color operand branches choose non-confusable color pairs and avoid near-color distractors.

## Annotation Contract
Annotation is a `keyed_bbox_set_map` with keys `left_operand` and `right_operand`. Each key maps to the list of `[x0, y0, x1, y1]` pixel boxes around the objects in that operand group. The keyed contract is required because difference queries need role binding; an unordered union of operand boxes would not fully ground the computation.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, operand groups, operand counts, arithmetic operation, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
