# `task_three_d__object_cluster__counterfactual_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
`count(filter(object_cluster_objects, predicate = target_predicate)) + edit_delta(target_predicate, single_exact_edit); scene=object_cluster; scope=counterfactual_count`

## Contract
The image shows many small synthetic perspective 3D objects arranged on a plain surface. This scene is a bare clustered-counting surface: it does not use option labels, named reference objects, relation prompts, or grid-based spatial cues.

The prompt asks for the final count of a queried property after applying exactly one textual add/remove edit to the visible starting cluster. The target predicate is one of:

- object type only, such as `cups`
- semantic color only, such as `blue [#1F77B4] objects`
- object type plus semantic color, such as `blue [#1F77B4] cups`

The edit always targets the exact queried property and changes the answer. Remove edits are generated only when enough starting target objects are visible, and generation keeps the final answer positive. Semantic color targets use the repo-wide canonical named color palette and prompt-facing hex labels.

The image includes non-target distractors. For color+object targets, generation includes structured partial-match distractors when possible, such as same-type/wrong-color and same-color/wrong-type objects. Wrong-type distractors avoid target-confusable object families such as card/envelope/book, sphere/button, cup/bowl/tray, lantern/candle, and pencil/ruler. The answer is computed from metadata as:

`initial_visible_target_count + add_amount` or `initial_visible_target_count - remove_amount`

Pixels are render output, not verifier source of truth.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around each starting visible object matching the queried property before the edit. The final answer can differ from the annotation cardinality because the prompt asks for the count after the hypothetical edit.

The annotation set is unordered because all visible witnesses have the same semantic role.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target predicate kind, initial target count, single counterfactual edit, edit amount, final target count, target object ids, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. The starting visual annotation and final counterfactual answer are recorded in the same finalized 3D scene trace.
