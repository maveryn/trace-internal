# `task_pages__sectioned_infographic__section_filtered_item_label`

## Identity
1. Domain: `pages`
2. Scene id: `sectioned_infographic`
3. Source task group: `infographic`
4. Task id: `task_pages__sectioned_infographic__section_filtered_item_label`

## Contract
1. Objective: find the unique listed item in a named section that has the requested visible marker shape.
2. Branch metadata: `query_id`
3. `query_id`: `section_filtered_item_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `section_title`, `filter_marker`, and `target_item` boxes.
6. Query knobs: target section, target marker, section count, item-count support, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `sectioned_infographic`
3. Task key: `sectioned_infographic_query`
4. Internal prompt variant key: `section_filtered_item_label`
5. Trace records section titles, item labels, marker types, marker bboxes, item-row bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized sectioned-infographic render metadata.
