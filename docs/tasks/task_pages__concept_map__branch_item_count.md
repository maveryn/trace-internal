# task_pages__concept_map__branch_item_count

## Identity
- domain: `pages`
- scene_id: `concept_map`
- task_group: `concept_map`

## Contract
Counts the direct child-item nodes connected to a named branch in a concept map.

Evidence is a `bbox_set` over the counted child-item nodes. The task uses branch membership from the rendered concept map, not graph reachability or node degree.
