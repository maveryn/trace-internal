# `task_graph__adjacency__traversal_kth_label`

## Summary
1. Domain: `graph`
2. Scene: `adjacency`
3. Task id: `task_graph__adjacency__traversal_kth_label`
4. Objective: return the node label at a requested position in a BFS or DFS traversal from an adjacency list.
5. Implementation: `trace/tasks/graph/adjacency/traversal_kth_label.py`.

## Query IDs
1. `bfs_kth_visit_label`: breadth-first search from a named source row, using each row's neighbor order left to right; the source node counts as visit position 1.
2. `dfs_kth_visit_label`: recursive depth-first search from a named source row, using each row's neighbor order left to right; the source node counts as visit position 1.

## Annotation
1. Answer type: `string`.
2. Annotation type: `bbox_sequence`.
3. Annotation boxes are `[x0,y0,x1,y1]` pixel boxes around the visited row labels, ordered from the source row through the answer row.

## Generation Notes
1. The scene renders a directed graph as an adjacency-list panel.
2. Default node count is `5..8`; default traversal position is `2..8`.
3. Every node is reachable from the sampled source row by construction.
4. Node labels use graph label variants `letters|numbers|named`.
5. The adjacency-list panel samples approved font families and readable list styles; non-answer header context chips may appear.
6. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.
