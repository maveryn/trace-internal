# `task_graph__binary_tree__node_property_count`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Task group: `counting`
4. Task id: `task_graph__binary_tree__node_property_count`
5. Objective: count nodes satisfying a binary-tree structural predicate.

## Query IDs
1. `leaf_node_count`: count nodes with no children.
2. `internal_node_count`: count nodes with at least one child.
3. `single_child_node_count`: count nodes with exactly one child.
4. `two_child_node_count`: count nodes with both left and right children.
5. `depth_level_node_count`: count nodes at a specified depth, with root depth `0`.

## Evidence
1. Answer type: `integer`.
2. Evidence type: `bbox_set`.
3. Evidence boxes are `[x0,y0,x1,y1]` pixel boxes around every counted node.

## Generation Notes
1. The renderer is a top-down ordered binary tree; left and right children are determined by visible position.
2. Default node count is `7..13`.
3. Node labels use graph label variants `letters|numbers|named`.
4. Query support is balanced by `query_id`; answer support is sampled independently from task-local count ranges.
5. `internal_node_count` uses feasible targets `3..7` with the default node-count range.
6. Title and node labels use the role-appropriate shared font pool and readable text styles with recorded contrast metadata.
