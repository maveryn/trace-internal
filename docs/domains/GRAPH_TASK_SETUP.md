# Graph Task Setup

## Purpose
Define the active graph-domain public task surface and shared scene contracts.

For cross-domain rollups, use `docs/project/STATUS.md` and `docs/ACTIVE_TASK_INVENTORY.md`. This file is the graph-domain contract for task design and implementation.

## Current Scope
1. `domain = graph`
2. Active `task_group`s: `counting`, `comparison`, `order`, `optimization`, `path`, `relation`
3. Active public graph task count: `40`

## Active Tasks

1. `task_graph__adjacency__component_count`
2. `task_graph__adjacency__mst_weight`
3. `task_graph__adjacency__traversal_kth_label`
4. `task_graph__automaton__accepted_string_label`
5. `task_graph__automaton__state_after_input_label`
6. `task_graph__binary_tree__node_property_count`
7. `task_graph__binary_tree__node_relation_label`
8. `task_graph__binary_tree__traversal_kth_label`
9. `task_graph__binary_tree__bst_path_operation_label`
10. `task_graph__binary_tree__heap_property_violation_label`
11. `task_graph__flow_network__max_flow_value`
12. `task_graph__flow_network__min_cut_edge_count`
13. `task_graph__graph_options__structure_match_label`
14. `task_graph__metro__exact_distance_station_count`
15. `task_graph__metro__shortest_path_length`
16. `task_graph__metro__station_membership_count`
17. `task_graph__metro__transfer_count`
18. `task_graph__node_link__articulation_point_count`
19. `task_graph__node_link__bridge_count`
20. `task_graph__node_link__common_neighbor_count`
21. `task_graph__node_link__component_membership_count`
22. `task_graph__node_link__cross_color_edge_count`
23. `task_graph__node_link__degree_extremum_value`
24. `task_graph__node_link__degree_predicate_count`
25. `task_graph__node_link__edge_attribute_label`
26. `task_graph__node_link__edge_color_count`
27. `task_graph__node_link__edge_text_count`
28. `task_graph__node_link__isolated_after_removal_count`
29. `task_graph__node_link__longest_path_length`
30. `task_graph__node_link__mst_weight`
31. `task_graph__node_link__named_node_degree_value`
32. `task_graph__node_link__node_color_count`
33. `task_graph__node_link__reachable_node_count`
34. `task_graph__node_link__shortest_path_length`
35. `task_graph__node_link__topological_position_value`
36. `task_graph__node_link__unique_cycle_size`
37. `task_graph__node_link__unique_node_label`
38. `task_graph__pipe_network__bridge_count`
39. `task_graph__pipe_network__junction_path_count`
40. `task_graph__pipe_network__shortest_path_length`

## Scene Contract
1. Simple undirected and directed node-link diagrams use `node_link`.
2. `pipe_network` renders labeled junctions connected by open or blocked pipe segments.
3. `metro` renders colored route lines with labeled stations.
4. `automaton` renders directed state-transition diagrams with start arrows, accepting-state rings, visible transition-symbol labels, and optional candidate-string panels.
5. `flow_network` renders directed capacity networks with source/sink roles and visible capacities.
6. `graph_options` renders one reference/target graph above six option graphs for structural matching and subgraph-selection tasks.
7. `binary_tree` renders one top-down ordered binary tree for binary-tree counting, traversal, node-relation, BST path-operation, and heap-property tasks.
8. `adjacency` renders adjacency-list, adjacency-matrix, and weighted-adjacency-matrix panels for representation-level graph reasoning.
9. Node-link scenes support layout variants `circular|shell|spring|grid_jitter|layered|component_clustered|path_spine|radial_tree`, node label variants `letters|numbers|named`, node glyph variants `circle|rounded_square|hexagon`, edge routing `straight|mixed_arc`, named node colors, and global layout transforms.
10. Node-link named labels use shared label manifests with task-specific length caps; metro, binary-tree, and adjacency-representation labels use tighter caps so labels remain legible. Pipe-network labels use compact letter/number labels only because the labels sit inside small physical fittings.
11. Node-link render audits use the role-appropriate shared font pool (`readout` for title/node/edge labels, `context` for optional non-answer context text), readable text styles, bounded graph-content jitter before evidence projection, and graph-appropriate plain/card/publication/print information-scene treatments; app/dashboard/console text chrome is excluded because it competes with prompt-facing graph labels. Optional non-answer context text can appear as title chips or reserved top/bottom/side blocks with sampled clutter levels; graph positions and evidence are projected after any block reservation.
12. Pipe-network renders use the role-appropriate shared font pool, readable text styles for title/junction labels, physical pipe-board styling with cylindrical tubes and flanged junction fittings, sampled board treatments (`plain_panel`, `plate_seams`, `perforated_panel`, and occasional `blueprint_grid`), optional non-answer context text, bounded content jitter before junction projection, and graph-domain post-render noise policy; blocked-pipe markers remain the primary scene-native distractors.
13. Metro renders use the role-appropriate shared font pool, readable text styles for station labels/title/legend, optional title-band context chips, bounded content jitter before station projection, and graph-domain post-render noise policy; colored route lines and the route legend remain the scene-native context.
14. Automaton renders use the role-appropriate shared font pool, readable text styles for state labels, transition labels, the start marker, and candidate strings, optional graph context text from the shared node-link renderer, bounded content jitter before state projection, and graph-domain post-render noise policy; start arrows, accepting-state rings, transition labels, and candidate-string panels remain scene-native context.
15. Binary-tree renders use the role-appropriate shared font pool, readable text styles for title and node labels, sampled tree treatments (`classic_tree`, `paper_tree`, `boxed_tree`), sampled node shapes/colors, and graph-domain post-render noise policy. Evidence boxes are projected from final node geometry; left/right child semantics come from horizontal placement in the ordered tree.
16. Flow-network renders use the role-appropriate shared font pool, readable text styles for title, node labels, and capacity labels, optional graph context text, bounded content jitter before node/edge projection, and graph-domain post-render noise policy. The layout remains layered left-to-right so the source-to-sink direction is readable; capacity labels are visible read-off text, while source/sink roles are identified by labels `S` and `T`.
17. Graph-options renders use the role-appropriate shared font pool, sampled panel/background/node-color styles, contrast-adjusted node fills for readable labels, per-panel graph-layout jitter within fixed option panels, final option-panel bboxes for evidence, and graph-domain post-render noise policy. Directed graph-options samples exclude anti-parallel edge pairs so opposite arrows do not overlap on one segment. Extra context text is intentionally omitted in this scene because the six option graphs are the visual distractors and additional prose would compete with option letters and node labels.
18. Adjacency renders use the role-appropriate shared font pool, readable text styles for panel titles, row/column labels, adjacency-list entries, and matrix cell values, sampled table/list panel styles (`clean_card`, `cool_sheet`, `warm_ledger`, `mint_index`, `ink_header`), optional non-answer header context chips, and graph-domain post-render noise policy. Evidence boxes are projected from final table/list cell geometry, while blank weighted-matrix cells remain visible by absence rather than by a text glyph.
19. Graph-domain post-render noise probability resolves to `0.50` for current graph generation. Calibration artifacts made before this standard can contain stale noise metadata.

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
2. Path tasks use `point_sequence`: an ordered array of `[x,y]` centers from start through end. Metro transfer-count evidence is the selected minimum-transfer station path in travel order, so the source is first, the required via station is included, and the goal is last.
3. Edge-count tasks with geometric edge evidence use `point_pair_set`: each item is a pair of endpoint-center points, and endpoint order inside each pair is semantically unordered.
4. Node-link tasks that answer with a node label but identify a graph node as the visual witness use `point_set` at the answer-node center; the visible label text is an identity attribute, not standalone evidence.
5. Visible text-label tasks use `bbox_set`: `[x0,y0,x1,y1]` pixel boxes around the visible label text.
6. Graph option-selection tasks use `bbox_set`: one `[x0,y0,x1,y1]` pixel box around the selected option panel.
7. Binary-tree count tasks use `bbox_set`: one node box per counted node.
8. Binary-tree traversal tasks use `bbox_sequence`: ordered node boxes from the first visited node through the answer node.
9. Binary-tree node-label relation tasks use `keyed_bbox_map`: role-bound node boxes such as `child`/`parent`, `parent`/`left_child`, `node`/`sibling`, or `node_a`/`node_b`/`lowest_common_ancestor`.
10. BST path-operation tasks use `bbox_sequence`: ordered operation-path node boxes from the root through the answer node.
11. Heap property-violation tasks use `bbox_sequence`: the checked parent node box followed by the violating child node box.
12. Adjacency-list traversal tasks use `bbox_sequence`: ordered row-label boxes from the source row through the answer row.
13. Adjacency component tasks use `bbox_set`: one representative row/header label box per connected component or strongly connected component.
14. Weighted adjacency-matrix MST tasks use `bbox_set`: one visible matrix-cell box per minimum-spanning-tree edge.
15. Automaton state-simulation and string-acceptance tasks use `point_sequence`: the visited state centers in transition order. String-acceptance evidence is one accepting state path for the candidate string whose option label is returned as the answer.
16. Evidence and answers must come from the same execution trace; verifiers rely on metadata/projections, not pixels.

## Implementation Notes
1. Retired task modules may remain as internal branch generators, but they are not imported by `trace/tasks/__init__.py`, not present in `TASK_TAXONOMY`, and not registered as default public tasks.
2. Public merged task outputs rewrite `scene_ir.task_id`, `query_spec.task_id`, and `execution_trace.task_id` to the merged task id while preserving concrete branch `query_id`.
3. Prompt text remains external to task code. Merged branches reuse the existing graph prompt bundles for their concrete `query_id`.
4. For any graph task with multiple query branches, the evidence instruction must be selected from the same concrete `query_id` as the question text. Avoid generic evidence wording such as "requested relation" when the branch is actually predecessor, successor, source, sink, add-edge, remove-edge, BFS, DFS, or a specific traversal order.
5. Solve-rate calibration for merged graph tasks should be regenerated after this consolidation.
