# `task_three_d__object_scene__counterfactual_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
`count_after_edits(filter(object_scene_objects, requested_attribute_predicate), edits); scene=object_scene; scope=counterfactual_count`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with projected objects, markers, references, or paired views depending on the task. The public task id defines the stable objective contract; query ids are used only for genuine semantic operations within that contract. Render style, camera, canvas preset, object placement, labels, colors, and prompt wording variants are generation metadata, not public task axes.

The verifier computes the answer from finalized scene metadata and projection records, not from pixels. The prompt bundle is `three_d_object_scene_v1` under `prompts/three_d/object_scene/`.

## Annotation Contract
Annotation is an unordered `bbox_set` containing one box around each counted object. The set may be empty when the answer is zero.
All witnesses have the same counted-object role, so ordering is not meaningful.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, object or marker records, rendered pixel witnesses, answer-support metadata, and the solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
