# `task_graph__binary_tree__tree_operation_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Task group: `relation`
4. Task id: `task_graph__binary_tree__tree_operation_label`
5. Objective: answer label-valued binary-search-tree or min-heap operation queries.

## Query Variants
1. `bst_search_terminal_label`: search for a key in a BST and answer the final visited node label.
2. `bst_insert_parent_label`: insert a missing key into a BST and answer the existing parent node label.
3. `heap_property_violation_label`: find the child node that violates the min-heap property.

## Evidence
1. Answer type: `string`.
2. Evidence type: `bbox_sequence`.
3. For BST queries, evidence boxes are the ordered search or insertion path from root through the answer node.
4. For heap violation queries, evidence boxes are the checked parent node followed by the violating child node.

## Generation Notes
1. BST variants render numeric keys in a bounded-depth binary search tree.
2. Heap variants render a complete numeric-key binary tree with exactly one min-heap violation.
3. Default node count is `7..13`.
4. The renderer is the shared top-down `binary_tree` scene.
