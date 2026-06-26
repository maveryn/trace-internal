# `task_three_d__object_scene__multiview_object_match_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`
- Annotation schema: `bbox`

## Program Contract
`select(label(second_view_floor_candidates, same_physical_object_as(red_boxed_reference_floor_object))); scene=object_scene; scope=multiview_object_match_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with projected objects, markers, references, or paired views depending on the task. The public task id defines the stable objective contract; query ids are used only for genuine semantic operations within that contract. Render style, camera, canvas preset, object placement, labels, colors, and prompt wording variants are generation metadata, not public task axes.

The verifier computes the answer from finalized scene metadata and projection records, not from pixels. The prompt bundle is `three_d_object_scene_v1` under `prompts/three_d/object_scene/`.

## Annotation Contract
Annotation is a scalar `bbox` around the selected matching object in the right view.
The left-view source object is visually marked by a red box and is retained in trace metadata for debugging, but it is not part of the requested annotation.

## Scene Construction
The task renders two camera views of the same scene. Four candidate floor objects share the same type and color, so object appearance does not identify the answer. A low rectangular platform with a raised corner block provides an asymmetric anchor, and the candidates are placed at different distances around that anchor.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, object or marker records, rendered pixel witnesses, answer-support metadata, and the solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
