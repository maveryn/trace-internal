# `task_pages__hierarchy__subtree_node_count`

## Identity
1. Domain: `pages`
2. Scene id: `hierarchy`
3. Task group: `hierarchy`

## Contract
Counts nodes in a subtree of one rooted hierarchy diagram.

Query ids: `subtree_descendant_count|subtree_leaf_count`.

Answers are integers. Evidence is a `bbox_set` over the counted node boxes.
