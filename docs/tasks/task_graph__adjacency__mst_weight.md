# `task_graph__adjacency__mst_weight`

## Summary
1. Domain: `graph`
2. Scene: `adjacency`
3. Task id: `task_graph__adjacency__mst_weight`
4. Objective: compute the total weight of the unique minimum spanning tree from a weighted adjacency matrix.
5. Implementation: `trace/tasks/graph/adjacency/mst_weight.py`.

## Query IDs
1. `weighted_matrix_mst_weight`: find the minimum spanning tree in a connected undirected weighted graph shown as a matrix.

## Annotation
1. Answer type: `integer`.
2. Annotation type: `bbox_set`.
3. Annotation boxes are `[x0,y0,x1,y1]` pixel boxes around the MST-edge matrix cell whose row label is topmost among the two endpoint rows.

## Generation Notes
1. Blank off-diagonal cells mean no edge; the diagonal uses `-`.
2. Default node count is `4..7`; default extra non-tree edge count is `1..3`.
3. Edge weights are sampled so the intended MST is unique.
4. Node labels use graph label variants `letters|numbers|named`.
5. The weighted matrix panel samples approved font families and readable table styles; non-answer header context chips may appear.
6. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.
