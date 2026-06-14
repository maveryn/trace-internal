# `task_pages__sectioned_infographic__section_item_count`

## Identity
1. Domain: `pages`
2. Scene id: `sectioned_infographic`
3. Source scene: `infographic`
4. Task id: `task_pages__sectioned_infographic__section_item_count`

## Contract
1. Objective: count the visible item rows listed in one named section of a sectioned infographic.
2. Branch metadata: `query_id`
3. `query_id`: `section_item_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over the visible item-row boxes in the requested section.
6. Query knobs: target section, section count, per-section item counts, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `sectioned_infographic`
3. Task key: `sectioned_infographic_query`
4. Internal prompt variant key: `section_item_count`
5. Trace records section titles, item labels, final section bboxes, final item-row bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized sectioned-infographic render metadata.
