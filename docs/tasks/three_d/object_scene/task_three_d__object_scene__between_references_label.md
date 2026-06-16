# `task_three_d__object_scene__between_references_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, two unlettered reference props named in the question, `6` unlettered answer candidates, and a below-scene text option panel.

The prompt asks which option describes the object between the two named reference objects. Generation places exactly one candidate in the floor-plane corridor between the references. The remaining candidates are placed outside that corridor and are constrained away from heavy visual overlap with either reference.

The answer is computed from metadata using each candidate's projected position along the reference-to-reference floor segment, lateral distance from that segment, and endpoint margin. Pixels are render output, not the verifier source of truth.

## Annotation Contract
Annotation is the bounding box of the selected 3D object in the scene. The two named reference objects are present in the trace and render map, but they are not part of the answer annotation; neither the option panel nor option text is annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference ids/names/shapes, per-label between metrics, per-label between truth values, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
