# `task_pages__mixed_infographic_page__module_field_ranked_item_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source task group: `infographic`
4. Task id: `task_pages__mixed_infographic_page__module_field_ranked_item_label`

## Contract
1. Objective: find the item label at a requested rank, such as second-highest or third-lowest, for a visible numeric field inside one titled module on a dense mixed infographic page.
2. Branch metadata: `query_id`
3. `query_id`: `module_field_ranked_item_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `module_title`, `field_label`, `ranked_item`, `ranked_value`, and `candidate_N` compared-value boxes.
6. Query knobs: target module, target numeric field, rank direction, rank position, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_field_ranked_item_label`
5. Trace records the candidate item values, parsed numeric values, rank direction, rank position, selected item, sampled style metadata, final bboxes, and layout geometry.
6. Generation requires enough unique numeric values for the requested rank by construction.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
