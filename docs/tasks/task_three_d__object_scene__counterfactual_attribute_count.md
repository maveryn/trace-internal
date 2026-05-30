# `task_three_d__object_scene__counterfactual_attribute_count`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `attribute_count_after_edits`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows the shared open synthetic perspective 3D object scene with a gridded floor or platform and many unlettered small 3D objects.

The prompt asks for the final count of a queried color-only, object-only, or color+object property, such as `red objects`, `cylinders`, or `red cylinders`, after applying one to three textual add/remove edits. The visible scene provides the starting count; the listed edits provide the counterfactual update steps.

Generation uses a narrow color-safe small-shape pool: ball, cube, cylinder, cone, ring, pyramid, and ramp. Prompt colors are controlled high-contrast colors: red, blue, green, yellow, purple, and orange. The scene includes non-target distractors and, when relevant, partial-match distractors so the initial visual count is grounded in the active predicate attributes.

Edit predicates can also be color-only, object-only, or color+object. Generation rejects any edit whose relationship to the final counted predicate would be ambiguous. Accepted edits either definitely affect the final predicate because the edit predicate is a subset of it, or definitely do not affect it because the edit predicate is disjoint from it. For two- and three-step instances, at least one edit changes the queried property and at least one edit is a distractor affecting a different property. The answer is computed from metadata: initial predicate counts plus the recorded edit deltas.

## Evidence Contract
Evidence is a `bbox_set` containing one whole-object bounding box for each visible starting object matching the final counted description before the edits. The final answer can differ from the number of evidence boxes because the prompt asks for the count after counterfactual textual edits.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`.

The trace records camera pose, projection frame, object world coordinates, prompt color names, fill RGB values, target predicate kind, target shape/color when active, initial property counts, initial target object ids, counterfactual add/remove steps, predicate relations, step deltas, and final symbolic count.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance evidence.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Initial visual evidence and counterfactual answer are recorded in the same execution trace.
