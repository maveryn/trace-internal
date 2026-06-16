# `task_three_d__object_scene__height_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query ids: `highest_above_floor`, `lowest_above_floor`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, larger support props, `5` unlettered small answer candidates placed at distinct heights above the floor, and a below-scene text option panel.

The prompt asks which option describes the object sitting highest or lowest above the floor. Generation constructs exactly one vertical extremum by placing candidates on the floor or on visible support props such as an open box, table, chair, and shelf. The answer is computed from each candidate object's metadata `base_xyz[2]` height above the floor, not from pixel position. Candidate object shapes are sampled from an expanded small-object pool. Prompt colors are assigned only after option labels are finalized, using the shared independent prompt-color policy, so support height cannot determine the answer color.

## Annotation Contract
Annotation is the bounding box of the selected 3D object in the scene. Larger support props are present in the trace and render map, but they are not part of the answer annotation; neither the option panel nor option text is annotation.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, support object ids, per-label vertical base heights, independent prompt-color metadata, the low-to-high height order, and option-panel descriptors/bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
