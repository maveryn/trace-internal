# `task_pages__category_grid__category_item_count`

## Identity
1. Domain: `pages`
2. Scene id: `category_grid`
3. Source scene package: `category_grid`
4. Task id: `task_pages__category_grid__category_item_count`

## Contract
1. Objective: count visible item rows inside a requested category and subcategory block.
2. Branch metadata: `query_id`
3. `query_id`: `category_item_count`
4. Answer type: `integer`
5. Annotation type: `bbox_set` over the counted item rows.
6. Query knobs: target category, target subcategory, category count, subcategory count, item-count support, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_category_grid_v0`
2. Scene key: `category_grid`
3. Task key: `category_grid_lookup_query`
4. Internal prompt variant key: `category_item_count`
5. Trace records category headers, subcategory headers, item order, item labels, final bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized category-grid render metadata.
