# `task_three_d__object_cluster__single_attribute_membership_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Query id: `type_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows a dense synthetic perspective 3D cluster of small objects on a plain surface. This scene is a bare clustered-counting surface: it does not use option labels, named reference objects, relation prompts, or grid-based spatial cues.

The prompt asks how many objects of one named type are present. The target type
is sampled from the full cluster object pool: the prompt-safe object-scene small
shapes plus CountQA-aligned loose objects such as writing tools, flat packets,
small tableware, hardware, containers, miniature furniture, plants, and game
pieces.

Generation samples a `cluster_composition_mode` axis:

- `single_type_cluster` (`0.6`): all visible objects are the target type, with answer/object count in `6-25`.
- `near_homogeneous_cluster` (`0.3`): the scene is mostly the target type with `1-4` visually distinct non-target distractors; target answer remains capped at `25`.
- `mixed_type_cluster` (`0.1`): the target type is counted among more varied distractor types, with target answer in `6-18`.

The default answer distribution is weighted over `6-10`, `11-17`, and `18-25`. Visually confusable same-family distractors are excluded for the selected target in modes that use distractors.

Prompt-facing wording must not mention absent labels, missing letters, or other non-present features for this scene. The prompt should describe only the visible scaffold and ask the count question directly.

The answer is the integer count of finalized objects whose `shape_type` equals the sampled target shape. Pixels are render output, not verifier source of truth.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each counted target object. The annotation set is unordered because all witnesses have the same semantic role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v0` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, target shape, target object ids, per-shape counts, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
