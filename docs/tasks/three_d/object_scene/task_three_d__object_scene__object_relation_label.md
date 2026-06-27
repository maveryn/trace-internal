# `task_three_d__object_scene__object_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`
- Annotation schema: `bbox`

## Program Contract
`select(label(candidate_objects, spatial_relation_to_reference = requested_relation)); scene=object_scene; scope=object_relation_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with projected objects, markers, references, or paired views depending on the task. The public task id defines the stable objective contract; query ids are used only for genuine semantic operations within that contract. Render style, camera, canvas preset, object placement, labels, colors, and prompt wording variants are generation metadata, not public task axes.

The verifier computes the answer from finalized scene metadata and projection records, not from pixels. The prompt bundle is `three_d_object_scene_v1` under `prompts/three_d/object_scene/`.

Candidate option objects are sampled from the curated object_scene-compatible
named-object pool derived from the domain-wide `THREE_D_NAMED_OBJECT_SHAPE_TYPES`
support. This excludes broad render-only small objects such as `drum` from named
MCQ candidates. Candidate objects are rendered with a relation-task scale
multiplier so they read as small props relative to the larger reference prop.
The same candidate object pool is used for every relation query id; query ids
change only the requested spatial relation and compatible reference prop.

## Annotation Contract
Annotation is a scalar `bbox` around the selected visible object.
The selected object is the only visual witness; option text is not annotation.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, object or marker records, rendered pixel witnesses, answer-support metadata, and the solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
