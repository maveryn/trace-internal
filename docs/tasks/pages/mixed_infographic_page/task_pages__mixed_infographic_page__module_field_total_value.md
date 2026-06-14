# `task_pages__mixed_infographic_page__module_field_total_value`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source scene: `mixed_infographic_page`
4. Task id: `task_pages__mixed_infographic_page__module_field_total_value`

## Contract
1. Objective: sum all visible values for one additive numeric field inside one titled module on a dense mixed infographic page.
2. Branch metadata: `query_id`
3. `query_id`: `module_field_total_value`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over every value cell used in the sum.
6. Query knobs: target module, target additive numeric field, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_mixed_infographic_page_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_field_total_value`
5. Trace records the summed item values, parsed numeric values, sampled style metadata, final bboxes, and layout geometry.
6. Additive fields are limited to `Score` and `Count`.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
