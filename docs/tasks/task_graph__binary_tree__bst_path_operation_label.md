# `task_graph__binary_tree__bst_path_operation_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Scene: `relation`
4. Task id: `task_graph__binary_tree__bst_path_operation_label`
5. Objective: answer label-valued binary-search-tree path operation queries.

## Query IDs
1. `bst_search_terminal_label`: search for a key in a BST and answer the final visited node label.
2. `bst_insert_parent_label`: insert a missing key into a BST and answer the existing parent node label.

## Annotation
1. Answer type: `string`.
2. Annotation type: `bbox_sequence`.
3. Annotation boxes are the ordered search or insertion path from the root through the answer node.

## Generation Notes
1. Instances render numeric keys in a bounded-depth binary search tree.
2. Default node count is `7..13`.
3. The renderer is the shared top-down `binary_tree` scene.
4. Title and node labels use the role-appropriate shared font pool and readable text styles with recorded contrast metadata.
5. Binary-tree rendering includes sampled tree treatments, node shapes/colors, light optional non-answer context text outside the tree content, bounded content jitter before projection, and scene-derived connector styles.
