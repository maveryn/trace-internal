# `task_pages__comparison_panel__side_attribute_value_label`

## Identity
1. Domain: `pages`
2. Scene id: `comparison_panel`
3. Source task group: `document_lookup`
4. Task id: `task_pages__comparison_panel__side_attribute_value_label`

## Contract
1. Objective: read the visible value at the intersection of a requested side/category header and shared attribute row.
2. Branch metadata: `query_id`
3. `query_id`: `side_attribute_value_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `side_header`, `attribute_label`, and `value_cell` boxes.
6. Query knobs: target side/category, target attribute row, side count, attribute count, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_document_lookup_v0`
2. Scene key: `comparison_panel`
3. Task key: `comparison_panel_lookup_query`
4. Internal prompt variant key: `side_attribute_value_label`
5. Trace records side headers, attribute labels, value-cell text, final bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized comparison-panel render metadata.
