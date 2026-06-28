# `task_three_d__object_scene__point_height_order_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation type: `point_set`
- Annotation schema: `point_set`

## Program Contract
`select(option_label(permutation(marked_points), order_by(height_from_floor, low_to_high))); scene=object_scene; scope=point_height_order_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with context objects and exactly three marked points at different heights above the floor. Each height point has a subtle guide stem to its floor projection, and the image includes a visual option panel with all six possible orders of the three point labels.

The verifier computes the true order from finalized 3D world-height metadata, not from pixels. Generation enforces visible point separation, readable guide stems, and a unique height order. Render style, camera, canvas preset, context objects, labels, colors, and prompt wording variants are generation metadata, not public task axes.

## Annotation Contract
Annotation is a `point_set` with multiple annotation witnesses: the centers of every marked point in the order task.
The guide stems and option panel are not annotation witnesses; the stems are visual support for height reading and the option panel maps the computed order to an answer label.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, point records, option descriptors, rendered pixel witnesses, answer-support metadata, and solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answer and annotation come from the same finalized 3D scene trace.
