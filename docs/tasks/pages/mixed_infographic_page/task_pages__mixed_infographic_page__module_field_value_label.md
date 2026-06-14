# `task_pages__mixed_infographic_page__module_field_value_label`

## Identity
1. Domain: `pages`
2. Scene id: `mixed_infographic_page`
3. Source scene: `mixed_infographic_page`
4. Task id: `task_pages__mixed_infographic_page__module_field_value_label`

## Contract
1. Objective: read the visible value at the intersection of a requested titled module, item label, and field label on a dense mixed infographic page with irregular module placement and mixed table, card, row, circular, ring-callout, and native contextual note treatments.
2. Branch metadata: `query_id`
3. `query_id`: `module_field_value_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `module_title`, `item_label`, `field_label`, and `value_cell` boxes.
6. Query knobs: target module, target item, target field, module count, per-module item/field counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_mixed_infographic_page_v0`
2. Scene key: `mixed_infographic_page`
3. Task key: `mixed_infographic_lookup_query`
4. Internal prompt variant key: `module_field_value_label`
5. Trace records module types, module titles, item labels, field labels, value-cell text, icon choices, sampled style metadata, page backdrop bands, native infographic text blocks, final bboxes, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized mixed-infographic render metadata.
7. Native text blocks, including two large paragraph-style panels, are part of the infographic scene and are recorded in `render_spec.infographic_text_blocks` and `render_map.infographic_text_block_bboxes_px`; they are not supporting annotation for this lookup task.

## Rendering Notes
1. The task disables the generic safe-margin pages context layer and instead draws 4-5 native text blocks inside reserved header/footer infographic regions, including two large wrapped paragraph panels.
2. A per-instance font profile samples readout, section-header, and accent-context families. Answer-bearing field labels, item labels, and values use the readout family; titles and native context blocks use the other sampled roles.
