# `task_three_d__object_scene__counterfactual_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Package: `trace/tasks/three_d/object_scene/`
- Query id: `attribute_count_after_edits`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform and many unlettered small 3D objects.

The prompt asks for the final count of a queried color-only, object-only, or color+object property, such as `red objects`, `cylinders`, or `red cylinders`, after applying one to three textual add/remove edits. The visible scene provides the starting count; the listed edits provide the counterfactual update steps.

Generation uses a narrow color-safe small-shape pool: ball, cube, cylinder, cone, ring, pyramid, and ramp. Prompt-facing named colors use the repo-wide canonical 10-color palette, with RGB values recorded in trace metadata and surfaced in prompts as `<color name> [#RRGGBB]`. The scene includes non-target distractors and, when relevant, partial-match distractors so the initial visual count is grounded in the active predicate attributes.

Edit predicates can also be color-only, object-only, or color+object. Generation rejects any edit whose relationship to the final counted predicate would be ambiguous. Accepted edits either definitely affect the final predicate because the edit predicate is a subset of it, or definitely do not affect it because the edit predicate is disjoint from it. For two- and three-step instances, at least one edit changes the queried property and at least one edit is a distractor affecting a different property. The answer is computed from metadata: initial predicate counts plus the recorded edit deltas.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-object bounding box for each visible starting object matching the final counted description before the edits. The final answer can differ from the number of annotation boxes because the prompt asks for the count after counterfactual textual edits.

## Prompt And Trace
The prompt bundle is `three_d_object_scene_v0` under `prompts/three_d/object_scene/`.

The trace records camera pose, projection frame, object world coordinates, prompt color names, fill RGB values, target predicate kind, target shape/color when active, initial property counts, initial target object ids, counterfactual add/remove steps, predicate relations, step deltas, and final symbolic count.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Initial visual annotation and counterfactual answer are recorded in the same execution trace.
