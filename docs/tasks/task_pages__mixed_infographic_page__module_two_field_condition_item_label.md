# `task_pages__mixed_infographic_page__module_two_field_condition_item_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source task group: `infographic`
4. Task id: `task_pages__mixed_infographic_page__module_two_field_condition_item_label`

## Contract
1. Objective: find the unique item label in one titled module that satisfies one numeric threshold condition and one categorical equality condition.
2. Branch metadata: `query_id`
3. `query_id`: `module_two_field_condition_item_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `module_title`, `numeric_field_label`, `category_field_label`, `matching_item`, `numeric_value_cell`, and `category_value_cell`.
6. Query knobs: target module, numeric field, categorical field, numeric operator, threshold, categorical value, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_two_field_condition_item_label`
5. Trace records both conditions, the unique matching item, per-condition match sets, sampled style metadata, final bboxes, and layout geometry.
6. Generation requires both individual conditions to leave multiple candidate items while their intersection has exactly one item.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
