# `task_graph__binary_tree__traversal_kth_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Scene: `order`
4. Task id: `task_graph__binary_tree__traversal_kth_label`
5. Objective: return the node label at a requested position in a binary-tree traversal.

## Query IDs
1. `preorder_kth_node_label`: root, left subtree, right subtree.
2. `inorder_kth_node_label`: left subtree, root, right subtree.
3. `postorder_kth_node_label`: left subtree, right subtree, root.
4. `level_order_kth_node_label`: top to bottom, left to right within each level.

## Annotation
1. Answer type: `string`.
2. Annotation type: `bbox_sequence`.
3. Annotation boxes are an ordered prefix of `[x0,y0,x1,y1]` pixel boxes, from the first visited node through the answer node.

## Generation Notes
1. The renderer is a top-down ordered binary tree; left and right children are determined by visible position.
2. Default node count is `7..13`; default requested traversal position is `2..10`.
3. Node labels use graph label variants `letters|numbers|named`.
4. Title and node labels use the role-appropriate shared font pool and readable text styles with recorded contrast metadata.
5. Binary-tree rendering includes sampled tree treatments, node shapes/colors, light optional non-answer context text outside the tree content, bounded content jitter before projection, and scene-derived connector styles.
