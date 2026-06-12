# `task_pages__mixed_infographic_page__module_field_extremum_item_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source scene: `mixed_infographic_page`
4. Task id: `task_pages__mixed_infographic_page__module_field_extremum_item_label`

## Contract
1. Objective: find the item label with the highest or lowest visible value for a requested numeric field inside one titled module on a dense mixed infographic page.
2. Branch metadata: `query_id`
3. `query_id`: `module_field_extremum_item_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `module_title`, `field_label`, `winning_item`, `winning_value`, and `candidate_N` compared-value boxes.
6. Query knobs: target module, target numeric field, rank direction, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_mixed_infographic_page_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_field_extremum_item_label`
5. Trace records the candidate item values, parsed numeric values, winning item, sampled style metadata, final bboxes, and layout geometry.
6. Generation requires a unique extremum by construction.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
