# `task_three_d__object_scene__occlusion_order_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, one unlettered reference prop named in the question, `6` unlettered answer candidates, and a below-scene text option panel. The reference prop is sampled from visually nameable occlusion targets such as an arch, bridge, table, shelf, or stand; open boxes are excluded here to avoid confusing "in front of" with the separate inside-container relation task.

The prompt asks which option describes the object that appears in front of the named reference object. Generation places exactly one candidate so that it visibly overlaps the reference in the camera view and is closer to the camera. The remaining candidates are placed so they do not meaningfully overlap the reference.

The answer is computed from metadata using projected object overlap and camera distance, not from pixels. The trace records overlap area and depth margin for every candidate label.

## Annotation Contract
Annotation is the bounding box of the selected 3D object in the scene. The named reference object is present in the trace and render map, but it is not part of the answer annotation; neither the option panel nor option text is annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference id/name/shape, per-label overlap areas, per-label depth margins, occlusion truth labels, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
