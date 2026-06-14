# `task_graph__binary_tree__heap_property_violation_label`

## Summary
1. Domain: `graph`
2. Scene: `binary_tree`
3. Scene: `relation`
4. Task id: `task_graph__binary_tree__heap_property_violation_label`
5. Objective: find the child node that violates a min-heap property.

## Query IDs
1. `heap_property_violation_label`: find the child node whose key is smaller than its parent key.

## Annotation
1. Answer type: `string`.
2. Annotation type: `keyed_bbox_map`.
3. Annotation uses keys `parent` and `child`, with each value a `[x0,y0,x1,y1]` pixel box around that node.

## Generation Notes
1. Instances render a complete numeric-key binary tree with exactly one min-heap violation.
2. Default node count is `7..13`.
3. The renderer is the shared top-down `binary_tree` scene.
4. Title and node labels use the role-appropriate shared font pool and readable text styles with recorded contrast metadata.
5. Binary-tree rendering includes sampled tree treatments, node shapes/colors, light optional non-answer context text outside the tree content, bounded content jitter before projection, and scene-derived connector styles.
