# `task_three_d__object_scene__marked_point_depth_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation type: `point`
- Annotation schema: `point`

## Program Contract
`select(label(floor_marked_points, extremum(camera_distance, requested_extremum))); scene=object_scene; scope=marked_point_depth_extremum_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with projected objects and lettered point markers placed on the floor plane. The public task id defines the stable objective contract; query ids select closest vs farthest marked floor point. Render style, camera, canvas preset, object placement, labels, colors, and prompt wording variants are generation metadata, not public task axes.

The verifier computes the answer from finalized floor-marker metadata and projection records, not from pixels. Generation also enforces that the selected closest/farthest floor marker is visually consistent with screen-depth ordering in the final perspective view. The prompt bundle is `three_d_object_scene_v1` under `prompts/three_d/object_scene/`.

## Annotation Contract
Annotation is a scalar `point` at the selected marked point center.
The selected marker center is the only visual witness; marker label text is used only to identify the answer option.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, object or marker records, rendered pixel witnesses, answer-support metadata, and the solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
