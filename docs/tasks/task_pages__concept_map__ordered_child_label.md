# task_pages__concept_map__ordered_child_label

## Identity
- domain: `pages`
- scene_id: `concept_map`
- task_group: `concept_map`

## Contract
Reads a specific ranked child-item label under a named concept-map branch. The query asks for an interior rank, sampled from the 2nd through 5th visible child item when available, using top-to-bottom reading order with left-to-right tie-breaking.

Evidence is a `bbox_set` containing the parent branch node and the answer child-item node.
