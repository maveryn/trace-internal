# `task_three_d__warehouse__scoped_attribute_count`

## Summary
- Domain: `three_d`
- Scene id: `warehouse`
- Public task id: `task_three_d__warehouse__scoped_attribute_count`
- Supported `query_id`: `top_shelf_item_count`, `middle_shelf_item_count`, `bottom_shelf_item_count`
- Answer schema: `integer`
- Annotation schema: `bbox_set`

## Program Contract
- Program schema: `count(filter(shelf_items, rack_color=target_color, shelf_level=target_level)); scene=warehouse; scope=scoped_attribute_count`
- Scene: `warehouse`
- Scope: `scoped_attribute_count`

Render one perspective warehouse shelf area with a gridded floor, two to four shelf racks, and visible countable shelf items. Each rack frame uses one unique canonical named prompt color, rendered with the same RGB triplet referenced in the prompt as `<color name> [#RRGGBB]`.

Every rack has exactly three shelf levels: bottom, middle, and top. The prompt asks how many items are on one specified shelf level of one specified colored rack. The queried rack is unique by color, and the answer range is `0..5` by construction. Distractors include items on other levels of the same rack and items on the queried level of other racks.

Annotation is a `bbox_set` containing one bounding box around each counted shelf item on the queried level of the queried rack. If the answer is `0`, annotation is an empty array. Rack frames, shelf beams, floor regions, and distractor items are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_warehouse_v1` under `prompts/three_d/warehouse/`. The trace records camera pose, projection frame, scene variant, aisle heading, rack colors, target rack id/color, target shelf level, per-rack shelf counts, all rack/item specs, target item ids, projected item bboxes, and the solver predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answer and annotation come from the same finalized 3D warehouse scene trace.
