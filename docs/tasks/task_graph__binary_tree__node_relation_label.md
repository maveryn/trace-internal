# `task_graph__binary_tree__node_relation_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Task group: `relation`
4. Task id: `task_graph__binary_tree__node_relation_label`
5. Objective: return a node label for a binary-tree structural relation.

## Query IDs
1. `parent_label`: answer the parent of a named node.
2. `left_child_label`: answer the left child of a named node.
3. `right_child_label`: answer the right child of a named node.
4. `sibling_label`: answer the sibling of a named node.
5. `lowest_common_ancestor_label`: answer the lowest common ancestor of two named nodes.

## Evidence
1. Answer type: `string`.
2. Evidence type: `bbox_set`.
3. Evidence boxes are `[x0,y0,x1,y1]` pixel boxes around the queried node or nodes and the answer node.

## Generation Notes
1. The renderer is a top-down ordered binary tree; left and right children are determined by visible position.
2. Default node count is `7..13`.
3. Node labels use graph label variants `letters|numbers|named`.
4. Query branches are sampled uniformly unless overridden by task config.
