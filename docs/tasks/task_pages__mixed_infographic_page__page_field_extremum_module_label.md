# `task_pages__mixed_infographic_page__page_field_extremum_module_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source task group: `infographic`
4. Task id: `task_pages__mixed_infographic_page__page_field_extremum_module_label`

## Contract
1. Objective: find the module title containing the highest or lowest visible value for a shared numeric field across a dense mixed infographic page.
2. Branch metadata: `query_id`
3. `query_id`: `page_field_extremum_module_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `winning_module_title`, `winning_field_label`, `winning_item`, `winning_value`, and `candidate_N` compared-value boxes.
6. Query knobs: target shared numeric field, rank direction, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `page_field_extremum_module_label`
5. Trace records the shared field label, compared page-wide item values, parsed numeric values, rank direction, winning item/module, sampled style metadata, final bboxes, and layout geometry.
6. Generation guarantees that the selected numeric field appears in at least three modules and has a unique page-wide extremum.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
