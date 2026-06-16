# `task_three_d__object_scene__object_relation_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Contract
The image shows the same open synthetic perspective 3D object scene as the camera-distance task: a gridded floor or platform, unlettered small answer-candidate objects, larger unlettered props, and a text option panel below the scene. The prompt asks which option describes the small object that has a spatial relation to a named prop.

The relation branch is recorded in `query_id`. `on_top_of_prop` samples a table, shelf, or stand; `under_prop` samples a bridge, arch, or table; `inside_prop` samples a low open box drawn like a tray so the contained object remains visible. Each instance constructs exactly one matching small object by world-coordinate placement, then places the remaining small objects outside that relation.

The shared scene camera samples front, side, and rear oblique orbit bands, so relation questions are viewed from varied 3D perspectives rather than one fixed side.

Each instance renders `6` small unlettered answer candidates and `2` larger context props. The answer is the matching option letter from the below-scene option panel, not the object name.

For `inside_prop`, the answer candidate is placed on the open-box floor rather than the world floor, the sampled answer shape is restricted to object types whose renderer supports elevated bases, and the contained answer uses a foreground render-order bias so the tray cannot paint over the correct option.

## Annotation Contract
Annotation is the bounding box of the selected small 3D object in the scene. The named prop is a reference object in the prompt and trace, but it is not included in the answer annotation; neither the option panel nor option text is annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, object roles, prompt-facing names, the reference prop id/name, per-label relation truth, projected object bboxes, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
