# `task_three_d__warehouse__scoped_attribute_count`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Task group: `warehouse`
- Query ids: `top_shelf_item_count`, `middle_shelf_item_count`, `bottom_shelf_item_count`
- Answer type: `integer`
- Annotation type: `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a clean synthetic perspective 3D warehouse shelf scene with a full-bleed gridded floor, `2` to `4` shelf racks, and visible countable shelf items. Each rack frame uses one unique canonical named prompt color, rendered with the same RGB triplet referenced in the prompt as `<color name> [#RRGGBB]`.

Every rack has exactly three shelf levels: bottom, middle, and top. The prompt asks how many items are on one specified shelf level of one specified colored rack. The queried rack is unique by color, and the answer range is `0..5` by construction. Distractors include items on other levels of the same rack and items on the queried level of other racks.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted shelf item on the queried level of the queried rack. If the answer is `0`, annotation is an empty array. Rack frames, shelf beams, floor regions, and distractor items are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v0` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, aisle heading, rack colors, target rack id/color, target shelf level, per-rack shelf counts, all rack/item specs, target item ids, projected item bboxes, and the solver predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D warehouse scene trace.
