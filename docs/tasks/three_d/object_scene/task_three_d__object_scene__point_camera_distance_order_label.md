# `task_three_d__object_scene__point_camera_distance_order_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation type: `point_map`
- Annotation schema: `point_map`

## Program Contract
`select(option_label(permutation(marked_points), order_by(camera_distance, near_to_far))); scene=object_scene; scope=point_camera_distance_order_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with context objects and exactly three marked floor points. The image includes a visual option panel with all six possible orders of the three point labels.

The verifier computes the true order from finalized 3D camera-distance metadata, not from pixels. Generation enforces visible point separation and a unique camera-distance order that is consistent with projected depth cues. Render style, camera, canvas preset, context objects, labels, colors, and prompt wording variants are generation metadata, not public task axes.

## Annotation Contract
Annotation is a `point_map` keyed by the visible point labels `P`, `Q`, and `R`; each value is the center of that marked point.
The option panel is not an annotation witness; it only maps the computed order to an answer label.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, point records, option descriptors, rendered pixel witnesses, answer-support metadata, and solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answer and annotation come from the same finalized 3D scene trace.
