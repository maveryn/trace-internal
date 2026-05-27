# Graph Task Setup

## Purpose
Define the active graph-domain public task surface and shared scene contracts.

For cross-domain rollups, use `docs/project/STATUS.md` and `docs/ACTIVE_TASK_INVENTORY.md`. This file is the graph-domain contract for task design and implementation.

## Current Scope
1. `domain = graph`
2. Active `task_group`s: `counting`, `comparison`, `order`, `optimization`, `path`, `relation`
3. Active public graph task count: `39`

## Active Tasks

1. `task_graph__adjacency__component_count`
2. `task_graph__adjacency__mst_weight`
3. `task_graph__adjacency__traversal_kth_label`
4. `task_graph__automaton__accepted_string_label`
5. `task_graph__automaton__state_after_input_label`
6. `task_graph__binary_tree__node_property_count`
7. `task_graph__binary_tree__node_relation_label`
8. `task_graph__binary_tree__traversal_kth_label`
9. `task_graph__binary_tree__tree_operation_label`
10. `task_graph__flow_network__max_flow_value`
11. `task_graph__flow_network__min_cut_edge_count`
12. `task_graph__graph_options__structure_match_label`
13. `task_graph__metro__exact_distance_station_count`
14. `task_graph__metro__shortest_path_length`
15. `task_graph__metro__station_membership_count`
16. `task_graph__metro__transfer_count`
17. `task_graph__node_link__articulation_point_count`
18. `task_graph__node_link__bridge_count`
19. `task_graph__node_link__common_neighbor_count`
20. `task_graph__node_link__component_membership_count`
21. `task_graph__node_link__cross_color_edge_count`
22. `task_graph__node_link__degree_extremum_value`
23. `task_graph__node_link__degree_predicate_count`
24. `task_graph__node_link__edge_attribute_label`
25. `task_graph__node_link__edge_color_count`
26. `task_graph__node_link__edge_text_count`
27. `task_graph__node_link__isolated_after_removal_count`
28. `task_graph__node_link__longest_path_length`
29. `task_graph__node_link__mst_weight`
30. `task_graph__node_link__named_node_degree_value`
31. `task_graph__node_link__node_color_count`
32. `task_graph__node_link__reachable_node_count`
33. `task_graph__node_link__shortest_path_length`
34. `task_graph__node_link__topological_position_value`
35. `task_graph__node_link__unique_cycle_size`
36. `task_graph__node_link__unique_node_label`
37. `task_graph__pipe_network__bridge_count`
38. `task_graph__pipe_network__junction_path_count`
39. `task_graph__pipe_network__shortest_path_length`

## Scene Contract
1. Simple undirected and directed node-link diagrams use `node_link`.
2. `pipe_network` renders labeled junctions connected by open or blocked pipe segments.
3. `metro` renders colored route lines with labeled stations.
4. `automaton` renders directed state-transition diagrams with start arrows, accepting-state rings, visible transition-symbol labels, and optional candidate-string panels.
5. `flow_network` renders directed capacity networks with source/sink roles and visible capacities.
6. `graph_options` renders one reference/target graph above six option graphs for structural matching and subgraph-selection tasks.
7. `binary_tree` renders one top-down ordered binary tree for binary-tree counting, traversal, node-relation, and search-tree operation tasks.
8. `adjacency` renders adjacency-list, adjacency-matrix, and weighted-adjacency-matrix panels for representation-level graph reasoning.
9. Node-link scenes support layout variants `circular|shell|spring|grid_jitter|layered|component_clustered|path_spine|radial_tree`, node label variants `letters|numbers|named`, node glyph variants `circle|rounded_square|hexagon`, edge routing `straight|mixed_arc`, named node colors, and global layout transforms.
10. Node-link named labels use shared label manifests with task-specific length caps; pipe, metro, binary-tree, and adjacency-representation labels use tighter caps so labels remain legible.
11. Graph-domain post-render noise probability resolves to `0.50` for current graph generation. Calibration artifacts made before this standard can contain stale noise metadata.

## Merged Public Tasks
1. `task_graph__node_link__degree_predicate_count`
   - Query ids: `undirected_degree_count`, `directed_in_degree_count`, `directed_out_degree_count`, `undirected_degree_one_filter_remaining_count`, `directed_in_degree_one_filter_remaining_count`, `directed_out_degree_one_filter_remaining_count`, `directed_source_count`, `directed_sink_count`
   - Reasoning pattern: count nodes satisfying a degree-style predicate.
   - Answer/evidence: `integer`, `point_set` of matching node centers.
   - Earlier narrower public ids were absorbed into these `query_id` branches and should not be reintroduced.
2. `task_graph__node_link__component_membership_count`
   - Query ids: `same_component_count`, `largest_component_size`, `component_size_after_edge_removal`, `component_size_after_edge_addition`
   - Reasoning pattern: count a connected-component node set under direct or one-edit hypothetical conditions.
   - Answer/evidence: `integer`, `point_set` of component node centers.
   - Earlier narrower public ids were absorbed into these `query_id` branches and should not be reintroduced.
3. `task_graph__node_link__reachable_node_count`
   - Query ids: `reachable_count`, `reachable_count_after_edge_removal`, `reachable_count_after_edge_addition`
   - Reasoning pattern: count nodes reachable from a query node in a directed graph before or after one hypothetical arrow edit.
   - Answer/evidence: `integer`, `point_set` of reachable node centers.
   - Earlier narrower public ids were absorbed into these `query_id` branches and should not be reintroduced.
4. `task_graph__metro__station_membership_count`
   - Query ids: `metro_transfer_station_count`, `metro_single_route_station_count`
   - Reasoning pattern: count stations satisfying a route-membership predicate.
   - Answer/evidence: `integer`, `point_set` of matching station centers.
   - Earlier narrower public ids were absorbed into these `query_id` branches and should not be reintroduced.

## Evidence Rules
1. Node and station count tasks use `point_set`: an unordered array of `[x,y]` pixel points at matching node/station centers.
2. Path tasks use `point_sequence`: an ordered array of `[x,y]` centers from start through end.
3. Edge-count tasks with geometric edge evidence use `point_pair_set`: each item is a pair of endpoint-center points.
4. Visible text-label tasks use `bbox_set`: `[x0,y0,x1,y1]` pixel boxes around the visible label text.
5. Graph option-selection tasks use `bbox_set`: one `[x0,y0,x1,y1]` pixel box around the selected option panel.
6. Binary-tree count tasks use `bbox_set`: one node box per counted node.
7. Binary-tree traversal tasks use `bbox_sequence`: ordered node boxes from the first visited node through the answer node.
8. Binary-tree node-label relation tasks use `bbox_set`: boxes around the queried node or nodes and the answer node.
9. Search-tree operation tasks use `bbox_sequence`: ordered operation-path node boxes, or parent then violating child for heap checks.
10. Adjacency-list traversal tasks use `bbox_sequence`: ordered row-label boxes from the source row through the answer row.
11. Adjacency component tasks use `bbox_set`: one representative row/header label box per connected component or strongly connected component.
12. Weighted adjacency-matrix MST tasks use `bbox_set`: one visible matrix-cell box per minimum-spanning-tree edge.
13. Automaton acceptance tasks use `point_sequence`: one valid accepting state path for the selected candidate string.
14. Evidence and answers must come from the same execution trace; verifiers rely on metadata/projections, not pixels.

## Implementation Notes
1. Retired task modules may remain as internal branch generators, but they are not imported by `trace/tasks/__init__.py`, not present in `TASK_TAXONOMY`, and not registered as default public tasks.
2. Public merged task outputs rewrite `scene_ir.task_id`, `query_spec.task_id`, and `execution_trace.task_id` to the merged task id while preserving concrete branch `query_id`.
3. Prompt text remains external to task code. Merged branches reuse the existing graph prompt bundles for their concrete `query_id`.
4. Solve-rate calibration for merged graph tasks should be regenerated after this consolidation.
