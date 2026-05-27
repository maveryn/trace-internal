# `task_graph__binary_tree__traversal_kth_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Task group: `order`
4. Task id: `task_graph__binary_tree__traversal_kth_label`
5. Objective: return the node label at a requested position in a binary-tree traversal.

## Query Variants
1. `preorder_kth_node_label`: root, left subtree, right subtree.
2. `inorder_kth_node_label`: left subtree, root, right subtree.
3. `postorder_kth_node_label`: left subtree, right subtree, root.
4. `level_order_kth_node_label`: top to bottom, left to right within each level.

## Evidence
1. Answer type: `string`.
2. Evidence type: `bbox_sequence`.
3. Evidence boxes are an ordered prefix of `[x0,y0,x1,y1]` pixel boxes, from the first visited node through the answer node.

## Generation Notes
1. The renderer is a top-down ordered binary tree; left and right children are determined by visible position.
2. Default node count is `7..13`; default requested traversal position is `2..10`.
3. Node labels use graph label variants `letters|numbers|named`.
