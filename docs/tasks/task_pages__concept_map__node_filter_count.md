# `task_pages__concept_map__node_filter_count`

## Identity
1. Domain: `pages`
2. Scene id: `concept_map`
3. Task group: `concept_map`

## Contract
Counts direct child-item nodes in one concept map that satisfy a branch or visible-marker predicate.

Query ids: `branch_child_count|marked_child_count`.

Answers are integers. Evidence is a `bbox_set` over the counted child-item nodes. The task uses rendered concept-map branch membership and markers, not graph reachability or node degree.
