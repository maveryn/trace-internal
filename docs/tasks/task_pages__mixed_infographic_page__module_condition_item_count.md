# `task_pages__mixed_infographic_page__module_condition_item_count`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source task group: `infographic`
4. Task id: `task_pages__mixed_infographic_page__module_condition_item_count`

## Contract
1. Objective: count the items in one titled mixed-infographic module whose visible numeric field value satisfies a threshold condition.
2. Branch metadata: `query_id`
3. `query_id`: `module_condition_item_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over the matching value cells.
6. Query knobs: target module, target numeric field, condition operator, threshold, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_condition_item_count`
5. Trace records the threshold, operator, candidate item values, matching item values, sampled style metadata, final bboxes, and layout geometry.
6. Threshold sampling keeps the answer nonzero and not all visible items.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
