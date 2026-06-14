# `task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source scene: `mixed_infographic_page`
4. Task id: `task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label`

## Contract
1. Objective: compare the totals for one shared additive field across two titled modules on a dense mixed infographic page and return the module title with the larger total.
2. Branch metadata: `query_id`
3. `query_id`: `two_module_field_total_comparison_module_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `module_a_title`, `module_b_title`, `field_label_a`, `field_label_b`, and `module_a_value_N` / `module_b_value_N` summed value-cell boxes.
6. Query knobs: target shared additive field, target module pair, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_mixed_infographic_page_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `two_module_field_total_comparison_module_label`
5. Trace records both module titles, shared field label, summed item values, computed module totals, winning module side, sampled style metadata, final bboxes, and layout geometry.
6. Generation guarantees that both selected modules contain the shared additive field and that the two totals are unequal.

## Rendering Notes
1. This task reuses the mixed-infographic renderer, native text blocks, page visual assets, and font profile.
2. Native context text and decorative assets are not answer annotation.
