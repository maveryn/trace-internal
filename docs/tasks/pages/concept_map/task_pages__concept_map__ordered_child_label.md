# task_pages__concept_map__ordered_child_label

## Identity
- domain: `pages`
- scene_id: `concept_map`
- scene_id: `concept_map`

## Contract
Reads a specific ranked child-item label under a named concept-map branch. The query asks for an interior rank, sampled from the 2nd through 5th visible child item when available, using top-to-bottom reading order with left-to-right tie-breaking.

Annotation is a `keyed_bbox_map` with `parent_branch` and `answer_child` boxes.
