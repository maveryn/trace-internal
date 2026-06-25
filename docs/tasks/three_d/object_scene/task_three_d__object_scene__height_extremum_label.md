# `task_three_d__object_scene__height_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Supported `query_id`: `highest_above_floor`, `lowest_above_floor`
- Answer type: `option_letter`
- Annotation type: `bbox`
- Annotation schema: `bbox`

## Program Contract
`select(label(candidate_objects, extremum(world_height_above_floor, requested_extremum))); scene=object_scene; scope=height_extremum_label`

## Contract
The image uses the `object_scene` renderer: a perspective 3D floor, table, or platform scene with projected objects, markers, references, or paired views depending on the task. The public task id defines the stable objective contract; query ids are used only for genuine semantic operations within that contract. Render style, camera, canvas preset, object placement, labels, colors, and prompt wording variants are generation metadata, not public task axes.

The verifier computes the answer from finalized scene metadata and projection records, not from pixels. The prompt bundle is `three_d_object_scene_v1` under `prompts/three_d/object_scene/`.

## Annotation Contract
Annotation is a scalar `bbox` around the selected visible object.
The selected object is the only visual witness; option text is not annotation.
The rendered task presents four option-panel candidates.
Candidate supports are limited to visually reliable floor/open-box/chair/shelf placements; tabletop placement is excluded because it can make objects appear under the table from some camera views.
Candidate object types are sampled without replacement from a narrow height-safe pool. The pool excludes objects with ambiguous support contact, weak semantic color rendering, or confusing height silhouettes. `cup` and `trophy` are allowed; `bottle`, `candle`, `drum`, `flask`, `goblet`, `hat`, and `lantern` are excluded.
Option descriptors use distinct object names only, not prompt-color names.

## Prompt And Trace
The trace records selected prompt keys, camera/projection data, object or marker records, rendered pixel witnesses, answer-support metadata, and the solver fields needed to recompute the answer and annotation from the same finalized scene.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
