# `task_graph__adjacency__component_count`

## Summary
1. Domain: `graph`
2. Scene: `adjacency`
3. Task group: `counting`
4. Task id: `task_graph__adjacency__component_count`
5. Objective: count connected components or strongly connected components from an adjacency representation.

## Query IDs
1. `undirected_component_count`: count connected components in an undirected graph.
2. `directed_strong_component_count`: count strongly connected components in a directed graph.

## Evidence
1. Answer type: `integer`.
2. Evidence type: `bbox_set`.
3. Evidence boxes are `[x0,y0,x1,y1]` pixel boxes around one representative row/header label from each counted component.

## Generation Notes
1. The scene renders either an adjacency list or an adjacency matrix.
2. Default node count is `6..9`; default component count is `2..6`.
3. Directed samples may include one-way edges between SCCs but preserve the requested SCC count.
4. Node labels use graph label variants `letters|numbers|named`.
5. The prompt names the concrete representation used in the image, not a combined list/matrix description.
6. The adjacency panel samples approved font families and readable table/list styles; non-answer header context chips may appear.
7. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.
