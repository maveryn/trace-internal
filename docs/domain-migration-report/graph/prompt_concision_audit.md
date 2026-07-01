# Prompt Concision Audit

- rendered prompts: `190`
- tasks covered: `60`
- observed query ids covered: `95`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_graph__adjacency__directed_pair_reciprocity_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__adjacency__directed_strong_component_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__adjacency__mst_weight | `single` | `{'single': 1}` | 2 | `` |
| task_graph__adjacency__traversal_kth_label | `bfs_kth_visit_label, dfs_kth_visit_label` | `{'bfs_kth_visit_label': 1, 'dfs_kth_visit_label': 1}` | 2 | `` |
| task_graph__adjacency__undirected_component_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__automaton__dfa_accepted_string_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__automaton__nfa_accepted_string_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__automaton__nondeterministic_state_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__automaton__state_after_input_label | `final_state_label, transition_step_state_label` | `{'final_state_label': 1, 'transition_step_state_label': 1}` | 2 | `` |
| task_graph__binary_tree__bst_path_operation_label | `bst_insert_parent_label, bst_search_terminal_label` | `{'bst_insert_parent_label': 1, 'bst_search_terminal_label': 1}` | 2 | `` |
| task_graph__binary_tree__child_structure_node_count | `internal_node_count, leaf_node_count, single_child_node_count, two_child_node_count` | `{'internal_node_count': 1, 'leaf_node_count': 1, 'single_child_node_count': 1, 'two_child_node_count': 1}` | 4 | `` |
| task_graph__binary_tree__depth_level_node_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__binary_tree__heap_property_violation_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__binary_tree__local_relative_node_label | `left_child_label, parent_label, right_child_label, sibling_label` | `{'left_child_label': 1, 'parent_label': 1, 'right_child_label': 1, 'sibling_label': 1}` | 4 | `` |
| task_graph__binary_tree__lowest_common_ancestor_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__binary_tree__traversal_kth_label | `inorder_kth_node_label, level_order_kth_node_label, postorder_kth_node_label, preorder_kth_node_label` | `{'inorder_kth_node_label': 1, 'level_order_kth_node_label': 1, 'postorder_kth_node_label': 1, 'preorder_kth_node_label': 1}` | 4 | `` |
| task_graph__flow_network__max_flow_value | `single` | `{'single': 1}` | 2 | `` |
| task_graph__flow_network__min_cut_edge_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__graph_options__contained_subgraph_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__graph_options__same_structure_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__metro__exact_distance_station_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__metro__route_condition_station_count | `metro_route_single_route_station_count, metro_route_transfer_station_count` | `{'metro_route_single_route_station_count': 1, 'metro_route_transfer_station_count': 1}` | 2 | `` |
| task_graph__metro__shortest_path_length | `single` | `{'single': 1}` | 2 | `` |
| task_graph__metro__station_membership_count | `metro_single_route_station_count, metro_transfer_station_count` | `{'metro_single_route_station_count': 1, 'metro_transfer_station_count': 1}` | 2 | `` |
| task_graph__node_link__articulation_point_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__bridge_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__common_related_node_count | `directed_common_predecessor_count, directed_common_successor_count, undirected_common_neighbor_count` | `{'directed_common_predecessor_count': 1, 'directed_common_successor_count': 1, 'undirected_common_neighbor_count': 1}` | 3 | `` |
| task_graph__node_link__component_size_after_edge_edit | `component_size_after_edge_addition, component_size_after_edge_removal` | `{'component_size_after_edge_addition': 1, 'component_size_after_edge_removal': 1}` | 2 | `` |
| task_graph__node_link__cross_color_edge_count | `cross_color_edge_count, directed_cross_color_edge_count` | `{'cross_color_edge_count': 1, 'directed_cross_color_edge_count': 1}` | 2 | `` |
| task_graph__node_link__degree_after_removal_filter_count | `directed_in_degree_one_filter_remaining_count, directed_out_degree_one_filter_remaining_count, undirected_degree_one_filter_remaining_count` | `{'directed_in_degree_one_filter_remaining_count': 1, 'directed_out_degree_one_filter_remaining_count': 1, 'undirected_degree_one_filter_remaining_count': 1}` | 3 | `` |
| task_graph__node_link__degree_extremum_value | `directed_max_in_degree_value, directed_max_out_degree_value, undirected_max_degree_value, undirected_min_degree_value` | `{'directed_max_in_degree_value': 1, 'directed_max_out_degree_value': 1, 'undirected_max_degree_value': 1, 'undirected_min_degree_value': 1}` | 4 | `` |
| task_graph__node_link__degree_value_filter_count | `directed_in_degree_count, directed_out_degree_count, undirected_degree_count` | `{'directed_in_degree_count': 1, 'directed_out_degree_count': 1, 'undirected_degree_count': 1}` | 3 | `` |
| task_graph__node_link__edge_between_nodes_label | `directed_edge_between_nodes_label, edge_between_nodes_label` | `{'directed_edge_between_nodes_label': 1, 'edge_between_nodes_label': 1}` | 2 | `` |
| task_graph__node_link__edge_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__edge_text_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__hamiltonian_cycle_neighbor_label | `next_in_hamiltonian_cycle_label, previous_in_hamiltonian_cycle_label` | `{'next_in_hamiltonian_cycle_label': 1, 'previous_in_hamiltonian_cycle_label': 1}` | 2 | `` |
| task_graph__node_link__isolated_after_removal_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__largest_chordless_cycle_size | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__largest_component_size | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__longest_path_length | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__mst_weight | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__named_node_degree_value | `directed_named_node_in_degree_value, directed_named_node_out_degree_value, directed_named_node_total_degree_value, undirected_named_node_degree_value` | `{'directed_named_node_in_degree_value': 1, 'directed_named_node_out_degree_value': 1, 'directed_named_node_total_degree_value': 1, 'undirected_named_node_degree_value': 1}` | 4 | `` |
| task_graph__node_link__node_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__reachable_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__reachable_count_after_edge_edit | `reachable_count_after_edge_addition, reachable_count_after_edge_removal` | `{'reachable_count_after_edge_addition': 1, 'reachable_count_after_edge_removal': 1}` | 2 | `` |
| task_graph__node_link__same_component_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__shortest_path_length | `directed_shortest_path_length, undirected_shortest_path_length` | `{'directed_shortest_path_length': 1, 'undirected_shortest_path_length': 1}` | 2 | `` |
| task_graph__node_link__topological_endpoint_node_label | `first_in_topological_order_label, last_in_topological_order_label` | `{'first_in_topological_order_label': 1, 'last_in_topological_order_label': 1}` | 2 | `` |
| task_graph__node_link__unique_cycle_size | `single` | `{'single': 1}` | 2 | `` |
| task_graph__node_link__unique_related_node_label | `unique_neighbor_label, unique_predecessor_label, unique_successor_label` | `{'unique_neighbor_label': 1, 'unique_predecessor_label': 1, 'unique_successor_label': 1}` | 3 | `` |
| task_graph__pedigree_chart__relatedness_coefficient_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__pedigree_chart__relationship_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__phylogeny_tree__clade_leaf_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__phylogeny_tree__mrca_clade_membership_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__phylogeny_tree__sister_leaf_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__phylogeny_tree__topology_outlier_label | `single` | `{'single': 1}` | 2 | `` |
| task_graph__pipe_network__bridge_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__pipe_network__pipe_exact_distance_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__pipe_network__pipe_reachable_junction_count | `single` | `{'single': 1}` | 2 | `` |
| task_graph__pipe_network__shortest_path_length | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_graph__automaton__nondeterministic_state_count / answer_and_annotation / sample 3682675236471242

- `query_id`: `single`
- `instance_seed`: `3682675236471242`
- `word_count`: `116`
- `body_word_count`: `49`

```text
The diagram shows a state-transition diagram with a start arrow, double-ring accepting states, and visible transition labels, including possible eps labels. How many states have nondeterministic outgoing transitions? Count a state if it has an outgoing eps transition or two or more outgoing transitions with the same input label.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every state that has an outgoing eps transition or two or more outgoing transitions with the same input label; use an empty array when the answer is zero.
Required answer format: set "answer" to the count of those states as an integer.
Example JSON:
{"annotation":[[150,250],[310,190]],"answer":2}
```

### task_graph__pipe_network__bridge_count / answer_and_annotation / sample 150369676515663

- `query_id`: `single`
- `instance_seed`: `150369676515663`
- `word_count`: `110`
- `body_word_count`: `34`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the open pipe segments whose removal would split the connected open-pipe network.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a junction center of one open pipe whose removal disconnects part of the open network; use [] when the answer is zero.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[[180,220],[310,220]],[[310,220],[430,300]]],"answer":2}
```

### task_graph__automaton__nfa_accepted_string_label / answer_and_annotation / sample 8826573100994865

- `query_id`: `single`
- `instance_seed`: `8826573100994865`
- `word_count`: `109`
- `body_word_count`: `43`

```text
The figure shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Starting at the start state, which candidate input can reach an accepting state in this nondeterministic automaton after all symbols are read?
Answer format: set "answer" to the option label of the accepted candidate string as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of one accepting NFA path for the returned option label's candidate string, starting with the start state and ending at an accepting state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__automaton__dfa_accepted_string_label / answer_and_annotation / sample 1092150697657127

- `query_id`: `single`
- `instance_seed`: `1092150697657127`
- `word_count`: `107`
- `body_word_count`: `37`

```text
The visual shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Choose the candidate string that ends in an accepting state when read by the deterministic automaton.
Final answer format: set "answer" to the option label of the accepted candidate string as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states on the accepting DFA path for the returned option label's candidate string, starting with the start state and ending at an accepting state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__adjacency__traversal_kth_label / answer_and_annotation / sample 6157950496189397

- `query_id`: `bfs_kth_visit_label`
- `instance_seed`: `6157950496189397`
- `word_count`: `106`
- `body_word_count`: `38`

```text
The figure shows a directed graph as an adjacency list. Starting from node B, perform breadth-first search reading each neighbor row from left to right. Which node is visited at position 2, counting the start as position 1?
Annotation format: set "annotation" to an ordered JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the row labels visited by breadth-first search from the source row through the answer row.
Answer format: set "answer" to the node label at the requested visit position as a string.
Example JSON:
{"annotation":[[70,126,158,158],[70,174,158,206],[70,222,158,254]],"answer":"M"}
```

### task_graph__adjacency__traversal_kth_label / answer_and_annotation / sample 6940680504626669

- `query_id`: `dfs_kth_visit_label`
- `instance_seed`: `6940680504626669`
- `word_count`: `104`
- `body_word_count`: `35`

```text
The panel shows a directed graph as an adjacency list. Run DFS beginning at node "India" with neighbors read left to right. Counting the source as position 1, which node is at visit position 4?
Final answer format: set "answer" to the node label at the requested visit position as a string.
Annotation format: set "annotation" to an ordered JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the row labels visited by depth-first search from the source row through the answer row.
Example JSON:
{"annotation":[[70,126,158,158],[70,174,158,206],[70,222,158,254]],"answer":"M"}
```

### task_graph__node_link__mst_weight / answer_and_annotation / sample 680873991491731

- `query_id`: `single`
- `instance_seed`: `680873991491731`
- `word_count`: `103`
- `body_word_count`: `37`

```text
This diagram shows a labeled connected weighted graph. A spanning tree uses edges to connect all nodes and has no cycles. Among those trees, the minimum-weight one is unique. What is the sum of its edge weights?
Final answer format: set "answer" to the total weight of that minimum spanning tree as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge in the minimum spanning tree.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__flow_network__max_flow_value / answer_and_annotation / sample 4603383199440900

- `query_id`: `single`
- `instance_seed`: `4603383199440900`
- `word_count`: `101`
- `body_word_count`: `32`

```text
You are shown a directed capacity network with source S and sink T. What is the largest total flow that can be sent from S to T without exceeding any edge capacity?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a node center of one directed edge in a minimum S-T cut supporting the max-flow value.
Required answer format: set "answer" to the maximum flow value as an integer.
Example JSON:
{"annotation":[[[170,280],[330,210]],[[170,280],[330,350]]],"answer":5}
```

### task_graph__flow_network__min_cut_edge_count / answer_and_annotation / sample 3887705864169145

- `query_id`: `single`
- `instance_seed`: `3887705864169145`
- `word_count`: `99`
- `body_word_count`: `28`

```text
The visual shows a directed capacity network with source S and sink T. What is the number of directed edges in the minimum-capacity cut from S to T?
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a node center of one directed edge in the unique minimum S-T cut.
Answer format: set "answer" to the number of directed edges in the unique minimum S-T cut as an integer.
Example JSON:
{"annotation":[[[170,280],[330,210]],[[170,280],[330,350]]],"answer":2}
```

### task_graph__automaton__state_after_input_label / answer_and_annotation / sample 8184186881066692

- `query_id`: `transition_step_state_label`
- `instance_seed`: `8184186881066692`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The visual shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, after reading the first 4 symbols of input "010110", which state are you in?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states visited through the requested transition step, starting with the start state and ending at the answer state for that step.
Answer format: set "answer" to the reached state label as a string.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__node_link__cross_color_edge_count / answer_and_annotation / sample 6726574745274512

- `query_id`: `directed_cross_color_edge_count`
- `instance_seed`: `6726574745274512`
- `word_count`: `98`
- `body_word_count`: `24`

```text
The image shows a labeled directed graph with colored nodes. How many arrows go from a maroon [#963644] node to a red [#E63232] node?
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the source or target node center for one arrow from a maroon [#963644] node to a red [#E63232] node; use [] when the answer is zero.
Required answer format: set "answer" to the count of matching edges as an integer.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__pipe_network__shortest_path_length / answer_and_annotation / sample 5971122719632057

- `query_id`: `single`
- `instance_seed`: `5971122719632057`
- `word_count`: `98`
- `body_word_count`: `42`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Ignoring blocked pipes, what is the length in pipe segments of the shortest open route from junction V to junction B?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at junction centers along the unique shortest open route from V to B, including both endpoints.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,220],[430,300]],"answer":2}
```

### task_graph__binary_tree__traversal_kth_label / answer_and_annotation / sample 4731498538500545

- `query_id`: `level_order_kth_node_label`
- `instance_seed`: `4731498538500545`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Traverse the tree level by level from top to bottom and left to right. What label is at position 2?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the level-order traversal nodes from the first visited node through the answer node.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__node_link__cross_color_edge_count / answer_and_annotation / sample 5193411690173881

- `query_id`: `cross_color_edge_count`
- `instance_seed`: `5193411690173881`
- `word_count`: `96`
- `body_word_count`: `23`

```text
The diagram shows a labeled undirected graph with colored nodes. Count the edges whose endpoint nodes are colored cyan [#34C4E0] and purple [#963ACA].
Answer format: set "answer" to the count of matching edges as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge connecting a cyan [#34C4E0] node and a purple [#963ACA] node; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / answer_and_annotation / sample 5786724094523424

- `query_id`: `component_size_after_edge_addition`
- `instance_seed`: `5786724094523424`
- `word_count`: `94`
- `body_word_count`: `34`

```text
The image shows a labeled undirected graph. If an edge were added between node C and node Q, how many nodes, including node Q itself, would be in the same connected component as Q?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be in the same connected component as Q after adding an edge between C and Q, including Q.
Answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__automaton__state_after_input_label / answer_and_annotation / sample 6461496592643044

- `query_id`: `final_state_label`
- `instance_seed`: `6461496592643044`
- `word_count`: `93`
- `body_word_count`: `31`

```text
The diagram shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, follow input "100000". Which state do you end in?
Final answer format: set "answer" to the reached state label as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states visited while reading the full input string, starting with the start state and ending at the final answer state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__node_link__edge_color_count / answer_and_annotation / sample 4580126231793567

- `query_id`: `single`
- `instance_seed`: `4580126231793567`
- `word_count`: `93`
- `body_word_count`: `17`

```text
The image shows a labeled undirected graph with colored edges. How many edges are colored cyan [#34C4E0]?
Answer format: set "answer" to the count of matching edges as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge colored cyan [#34C4E0]; for directed graphs, use the source and target node centers; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / answer_and_annotation / sample 2974971322339970

- `query_id`: `component_size_after_edge_removal`
- `instance_seed`: `2974971322339970`
- `word_count`: `92`
- `body_word_count`: `29`

```text
The image shows a labeled undirected graph. Imagine deleting the edge between node K and node V. How many labeled nodes would remain connected to node K, including K?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be in the same connected component as K after removing the edge between K and V, including K.
Format for the "answer" field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__adjacency__mst_weight / answer_and_annotation / sample 3991265547348585

- `query_id`: `single`
- `instance_seed`: `3991265547348585`
- `word_count`: `91`
- `body_word_count`: `23`

```text
The visual shows a connected undirected weighted graph as a weighted adjacency matrix. What is the total weight of the minimum spanning tree?
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes in image pixel coordinates around the matrix cell for each minimum-spanning-tree edge whose row label is topmost among the two endpoint rows.
Answer format: set "answer" to the total weight of the minimum spanning tree as an integer.
Example JSON:
{"annotation":[[278,182,328,232],[328,282,378,332],[378,332,428,382]],"answer":12}
```

### task_graph__metro__shortest_path_length / answer_and_annotation / sample 3609314617225980

- `query_id`: `single`
- `instance_seed`: `3609314617225980`
- `word_count`: `91`
- `body_word_count`: `36`

```text
You are shown a labeled metro route map with colored routes and stations. The metro map has a unique shortest station path from station P to station L. How many route segments are in that path?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at station centers along the unique shortest path from P to L, excluding P and including L.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__adjacency__directed_pair_reciprocity_count / answer_and_annotation / sample 350235172879520

- `query_id`: `single`
- `instance_seed`: `350235172879520`
- `word_count`: `90`
- `body_word_count`: `21`

```text
The image shows a directed graph as an adjacency matrix. Count the unordered node pairs where both directed edges are present.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one mirrored matrix cell for one counted mutual node pair; use [] when the answer is zero.
Answer format: set "answer" to the number of counted unordered node pairs as an integer.
Example JSON:
{"annotation":[[[303,207],[353,157]]],"answer":1}
```

### task_graph__pipe_network__pipe_exact_distance_count / answer_and_annotation / sample 1876734353903208

- `query_id`: `single`
- `instance_seed`: `1876734353903208`
- `word_count`: `90`
- `body_word_count`: `35`

```text
The visual shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the junctions whose shortest open route from 16 uses exactly 3 pipe segments.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all junctions whose shortest open-pipe distance from 16 is exactly 3 segments.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,220],[430,300]],"answer":3}
```

### task_graph__binary_tree__lowest_common_ancestor_label / answer_and_annotation / sample 6370444253482048

- `query_id`: `single`
- `instance_seed`: `6370444253482048`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. For nodes "Era" and "Ubs", what label is on their deepest shared ancestor?
Annotation format: set "annotation" to a JSON object with keys "node_a", "node_b", and "lowest_common_ancestor"; each value is a [x,y] pixel point at that node center.
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"node_a":[180,148],"node_b":[495,455],"lowest_common_ancestor":[274,274]},"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / answer_and_annotation / sample 4269638941287360

- `query_id`: `preorder_kth_node_label`
- `instance_seed`: `4269638941287360`
- `word_count`: `89`
- `body_word_count`: `31`

```text
The diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Counting preorder visits from 1, what label appears at position 4?
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the preorder traversal nodes from the first visited node through the answer node.
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__node_link__reachable_count_after_edge_edit / answer_and_annotation / sample 8651274970261045

- `query_id`: `reachable_count_after_edge_removal`
- `instance_seed`: `8651274970261045`
- `word_count`: `89`
- `body_word_count`: `32`

```text
The figure shows a labeled directed graph. Imagine deleting the directed edge from node "Dux" to node "Bam". How many labeled nodes would remain reachable from "Dux" when arrow directions are followed?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be reachable from "Dux" after removing the arrow from "Dux" to "Bam", including "Dux".
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

## Repeated Scaffolding Terms

### task_graph__binary_tree__traversal_kth_label / answer_only / sample 4731498538500545

- `query_id`: `level_order_kth_node_label`
- `instance_seed`: `4731498538500545`
- `word_count`: `59`
- `body_word_count`: `55`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Traverse the tree level by level from top to bottom and left to right. What label is at position 2?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / answer_only / sample 413196834686146

- `query_id`: `parent_label`
- `instance_seed`: `413196834686146`
- `word_count`: `49`
- `body_word_count`: `45`
- `repeated_terms`: `{'answer': 3}`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. What is the label of the parent of node "Paa"?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__node_link__unique_related_node_label / answer_only / sample 4579128843647250

- `query_id`: `unique_neighbor_label`
- `instance_seed`: `4579128843647250`
- `word_count`: `35`
- `body_word_count`: `31`
- `repeated_terms`: `{'answer': 3}`

```text
The visual shows a labeled undirected graph. Which node is the only neighbor of node X?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"B"}
```

## All Prompt Samples

### task_graph__adjacency__directed_pair_reciprocity_count / single / answer_and_annotation / sample 350235172879520

- `instance_seed`: `350235172879520`
- `word_count`: `90`
- `body_word_count`: `21`

```text
The image shows a directed graph as an adjacency matrix. Count the unordered node pairs where both directed edges are present.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one mirrored matrix cell for one counted mutual node pair; use [] when the answer is zero.
Answer format: set "answer" to the number of counted unordered node pairs as an integer.
Example JSON:
{"annotation":[[[303,207],[353,157]]],"answer":1}
```

### task_graph__adjacency__directed_pair_reciprocity_count / single / answer_only / sample 350235172879520

- `instance_seed`: `350235172879520`
- `word_count`: `40`
- `body_word_count`: `21`

```text
The image shows a directed graph as an adjacency matrix. Count the unordered node pairs where both directed edges are present.
Answer format: set "answer" to the number of counted unordered node pairs as an integer.
Example JSON:
{"answer":1}
```

### task_graph__adjacency__directed_strong_component_count / single / answer_and_annotation / sample 7630128945771724

- `instance_seed`: `7630128945771724`
- `word_count`: `74`
- `body_word_count`: `18`

```text
You are shown a directed graph as an adjacency list. What is the number of strongly connected components?
Required annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes in image pixel coordinates around the topmost row label in each strongly connected component.
Required answer format: set "answer" to the number of strongly connected components as an integer.
Example JSON:
{"annotation":[[70,126,158,158],[70,318,158,350]],"answer":2}
```

### task_graph__adjacency__directed_strong_component_count / single / answer_only / sample 7630128945771724

- `instance_seed`: `7630128945771724`
- `word_count`: `39`
- `body_word_count`: `18`

```text
You are shown a directed graph as an adjacency list. What is the number of strongly connected components?
Format for the "answer" field: set "answer" to the number of strongly connected components as an integer.
Example JSON:
{"answer":2}
```

### task_graph__adjacency__mst_weight / single / answer_and_annotation / sample 3991265547348585

- `instance_seed`: `3991265547348585`
- `word_count`: `91`
- `body_word_count`: `23`

```text
The visual shows a connected undirected weighted graph as a weighted adjacency matrix. What is the total weight of the minimum spanning tree?
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes in image pixel coordinates around the matrix cell for each minimum-spanning-tree edge whose row label is topmost among the two endpoint rows.
Answer format: set "answer" to the total weight of the minimum spanning tree as an integer.
Example JSON:
{"annotation":[[278,182,328,232],[328,282,378,332],[378,332,428,382]],"answer":12}
```

### task_graph__adjacency__mst_weight / single / answer_only / sample 3991265547348585

- `instance_seed`: `3991265547348585`
- `word_count`: `44`
- `body_word_count`: `23`

```text
The visual shows a connected undirected weighted graph as a weighted adjacency matrix. What is the total weight of the minimum spanning tree?
Required answer format: set "answer" to the total weight of the minimum spanning tree as an integer.
Example JSON:
{"answer":12}
```

### task_graph__adjacency__traversal_kth_label / bfs_kth_visit_label / answer_and_annotation / sample 6157950496189397

- `instance_seed`: `6157950496189397`
- `word_count`: `106`
- `body_word_count`: `38`

```text
The figure shows a directed graph as an adjacency list. Starting from node B, perform breadth-first search reading each neighbor row from left to right. Which node is visited at position 2, counting the start as position 1?
Annotation format: set "annotation" to an ordered JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the row labels visited by breadth-first search from the source row through the answer row.
Answer format: set "answer" to the node label at the requested visit position as a string.
Example JSON:
{"annotation":[[70,126,158,158],[70,174,158,206],[70,222,158,254]],"answer":"M"}
```

### task_graph__adjacency__traversal_kth_label / bfs_kth_visit_label / answer_only / sample 6157950496189397

- `instance_seed`: `6157950496189397`
- `word_count`: `58`
- `body_word_count`: `38`

```text
The figure shows a directed graph as an adjacency list. Starting from node B, perform breadth-first search reading each neighbor row from left to right. Which node is visited at position 2, counting the start as position 1?
Answer format: set "answer" to the node label at the requested visit position as a string.
Example JSON:
{"answer":"M"}
```

### task_graph__adjacency__traversal_kth_label / dfs_kth_visit_label / answer_and_annotation / sample 6940680504626669

- `instance_seed`: `6940680504626669`
- `word_count`: `104`
- `body_word_count`: `35`

```text
The panel shows a directed graph as an adjacency list. Run DFS beginning at node "India" with neighbors read left to right. Counting the source as position 1, which node is at visit position 4?
Final answer format: set "answer" to the node label at the requested visit position as a string.
Annotation format: set "annotation" to an ordered JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the row labels visited by depth-first search from the source row through the answer row.
Example JSON:
{"annotation":[[70,126,158,158],[70,174,158,206],[70,222,158,254]],"answer":"M"}
```

### task_graph__adjacency__traversal_kth_label / dfs_kth_visit_label / answer_only / sample 6940680504626669

- `instance_seed`: `6940680504626669`
- `word_count`: `58`
- `body_word_count`: `35`

```text
The panel shows a directed graph as an adjacency list. Run DFS beginning at node "India" with neighbors read left to right. Counting the source as position 1, which node is at visit position 4?
Format for the "answer" field: set "answer" to the node label at the requested visit position as a string.
Example JSON:
{"answer":"M"}
```

### task_graph__adjacency__undirected_component_count / single / answer_and_annotation / sample 7826047401875681

- `instance_seed`: `7826047401875681`
- `word_count`: `69`
- `body_word_count`: `17`

```text
The panel shows an undirected graph as an adjacency matrix. What is the number of connected components?
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes in image pixel coordinates around the topmost row label in each connected component.
Answer format: set "answer" to the number of connected components as an integer.
Example JSON:
{"annotation":[[70,126,158,158],[70,318,158,350]],"answer":2}
```

### task_graph__adjacency__undirected_component_count / single / answer_only / sample 7826047401875681

- `instance_seed`: `7826047401875681`
- `word_count`: `34`
- `body_word_count`: `30`

```text
The panel shows an undirected graph as an adjacency matrix. What is the number of connected components?
Answer field: set "answer" to the number of connected components as an integer.
Example JSON:
{"answer":2}
```

### task_graph__automaton__dfa_accepted_string_label / single / answer_and_annotation / sample 1092150697657127

- `instance_seed`: `1092150697657127`
- `word_count`: `107`
- `body_word_count`: `37`

```text
The visual shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Choose the candidate string that ends in an accepting state when read by the deterministic automaton.
Final answer format: set "answer" to the option label of the accepted candidate string as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states on the accepting DFA path for the returned option label's candidate string, starting with the start state and ending at an accepting state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__automaton__dfa_accepted_string_label / single / answer_only / sample 1092150697657127

- `instance_seed`: `1092150697657127`
- `word_count`: `60`
- `body_word_count`: `37`

```text
The visual shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Choose the candidate string that ends in an accepting state when read by the deterministic automaton.
Format for the "answer" field: set "answer" to the option label of the accepted candidate string as a string.
Example JSON:
{"answer":"C"}
```

### task_graph__automaton__nfa_accepted_string_label / single / answer_and_annotation / sample 8826573100994865

- `instance_seed`: `8826573100994865`
- `word_count`: `109`
- `body_word_count`: `43`

```text
The figure shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Starting at the start state, which candidate input can reach an accepting state in this nondeterministic automaton after all symbols are read?
Answer format: set "answer" to the option label of the accepted candidate string as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of one accepting NFA path for the returned option label's candidate string, starting with the start state and ending at an accepting state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__automaton__nfa_accepted_string_label / single / answer_only / sample 8826573100994865

- `instance_seed`: `8826573100994865`
- `word_count`: `63`
- `body_word_count`: `59`

```text
The figure shows a state-transition diagram with a start arrow, double-ring accepting states, visible transition labels, and labeled candidate input strings. Starting at the start state, which candidate input can reach an accepting state in this nondeterministic automaton after all symbols are read?
Answer field: set "answer" to the option label of the accepted candidate string as a string.
Example JSON:
{"answer":"C"}
```

### task_graph__automaton__nondeterministic_state_count / single / answer_and_annotation / sample 3682675236471242

- `instance_seed`: `3682675236471242`
- `word_count`: `116`
- `body_word_count`: `49`

```text
The diagram shows a state-transition diagram with a start arrow, double-ring accepting states, and visible transition labels, including possible eps labels. How many states have nondeterministic outgoing transitions? Count a state if it has an outgoing eps transition or two or more outgoing transitions with the same input label.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every state that has an outgoing eps transition or two or more outgoing transitions with the same input label; use an empty array when the answer is zero.
Required answer format: set "answer" to the count of those states as an integer.
Example JSON:
{"annotation":[[150,250],[310,190]],"answer":2}
```

### task_graph__automaton__nondeterministic_state_count / single / answer_only / sample 3682675236471242

- `instance_seed`: `3682675236471242`
- `word_count`: `66`
- `body_word_count`: `49`

```text
The diagram shows a state-transition diagram with a start arrow, double-ring accepting states, and visible transition labels, including possible eps labels. How many states have nondeterministic outgoing transitions? Count a state if it has an outgoing eps transition or two or more outgoing transitions with the same input label.
Answer format: set "answer" to the count of those states as an integer.
Example JSON:
{"answer":2}
```

### task_graph__automaton__state_after_input_label / final_state_label / answer_and_annotation / sample 6461496592643044

- `instance_seed`: `6461496592643044`
- `word_count`: `93`
- `body_word_count`: `31`

```text
The diagram shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, follow input "100000". Which state do you end in?
Final answer format: set "answer" to the reached state label as a string.
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states visited while reading the full input string, starting with the start state and ending at the final answer state.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__automaton__state_after_input_label / final_state_label / answer_only / sample 6461496592643044

- `instance_seed`: `6461496592643044`
- `word_count`: `50`
- `body_word_count`: `31`

```text
The diagram shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, follow input "100000". Which state do you end in?
Format for the "answer" field: set "answer" to the reached state label as a string.
Example JSON:
{"answer":"C"}
```

### task_graph__automaton__state_after_input_label / transition_step_state_label / answer_and_annotation / sample 8184186881066692

- `instance_seed`: `8184186881066692`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The visual shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, after reading the first 4 symbols of input "010110", which state are you in?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at the centers of the states visited through the requested transition step, starting with the start state and ending at the answer state for that step.
Answer format: set "answer" to the reached state label as a string.
Example JSON:
{"annotation":[[150,250],[310,190],[480,230]],"answer":"C"}
```

### task_graph__automaton__state_after_input_label / transition_step_state_label / answer_only / sample 8184186881066692

- `instance_seed`: `8184186881066692`
- `word_count`: `52`
- `body_word_count`: `36`

```text
The visual shows a deterministic state-transition diagram with a start arrow, double-ring accepting states, and transition labels. Starting at the start state, after reading the first 4 symbols of input "010110", which state are you in?
Answer format: set "answer" to the reached state label as a string.
Example JSON:
{"answer":"C"}
```

### task_graph__binary_tree__bst_path_operation_label / bst_insert_parent_label / answer_and_annotation / sample 380024452560000

- `instance_seed`: `380024452560000`
- `word_count`: `83`
- `body_word_count`: `24`

```text
The figure shows a numeric-key binary search tree. Follow the BST insertion path for key 81. Which existing node label would become the parent?
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the visited insertion path from the root through the parent node where the new key would attach.
Answer format: set "answer" to the answer node key as a string exactly as shown.
Example JSON:
{"annotation":[[180,148],[274,274]],"answer":"42"}
```

### task_graph__binary_tree__bst_path_operation_label / bst_insert_parent_label / answer_only / sample 380024452560000

- `instance_seed`: `380024452560000`
- `word_count`: `44`
- `body_word_count`: `24`

```text
The figure shows a numeric-key binary search tree. Follow the BST insertion path for key 81. Which existing node label would become the parent?
Final answer format: set "answer" to the answer node key as a string exactly as shown.
Example JSON:
{"answer":"42"}
```

### task_graph__binary_tree__bst_path_operation_label / bst_search_terminal_label / answer_and_annotation / sample 8580041359586820

- `instance_seed`: `8580041359586820`
- `word_count`: `80`
- `body_word_count`: `26`

```text
The image shows a numeric-key binary search tree. If you search this BST for 72, what label is on the terminal node of the search path?
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the visited binary-search path from the root through the answer node.
Required answer format: set "answer" to the answer node key as a string exactly as shown.
Example JSON:
{"annotation":[[180,148],[274,274]],"answer":"42"}
```

### task_graph__binary_tree__bst_path_operation_label / bst_search_terminal_label / answer_only / sample 8580041359586820

- `instance_seed`: `8580041359586820`
- `word_count`: `46`
- `body_word_count`: `26`

```text
The image shows a numeric-key binary search tree. If you search this BST for 72, what label is on the terminal node of the search path?
Final answer format: set "answer" to the answer node key as a string exactly as shown.
Example JSON:
{"answer":"42"}
```

### task_graph__binary_tree__child_structure_node_count / internal_node_count / answer_and_annotation / sample 8565451818268265

- `instance_seed`: `8565451818268265`
- `word_count`: `82`
- `body_word_count`: `32`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. How many nodes have a left child, a right child, or both?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every internal node, meaning every non-leaf node; use [] when the answer is zero.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[180,148],[495,455]],"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / internal_node_count / answer_only / sample 8565451818268265

- `instance_seed`: `8565451818268265`
- `word_count`: `47`
- `body_word_count`: `32`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. How many nodes have a left child, a right child, or both?
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / leaf_node_count / answer_and_annotation / sample 3979447975631251

- `instance_seed`: `3979447975631251`
- `word_count`: `72`
- `body_word_count`: `26`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. How many leaf nodes are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every leaf node; use [] when the answer is zero.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[180,148],[495,455]],"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / leaf_node_count / answer_only / sample 3979447975631251

- `instance_seed`: `3979447975631251`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. How many leaf nodes are there?
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / single_child_node_count / answer_and_annotation / sample 2557643600253586

- `instance_seed`: `2557643600253586`
- `word_count`: `79`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. Count the nodes with one child. How many are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node with exactly one child; use [] when the answer is zero.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[180,148],[495,455]],"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / single_child_node_count / answer_only / sample 2557643600253586

- `instance_seed`: `2557643600253586`
- `word_count`: `45`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. Count the nodes with one child. How many are there?
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / two_child_node_count / answer_and_annotation / sample 2863496891276065

- `instance_seed`: `2863496891276065`
- `word_count`: `80`
- `body_word_count`: `30`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Find every node with two children. How many are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node with both left and right children; use [] when the answer is zero.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[180,148],[495,455]],"answer":2}
```

### task_graph__binary_tree__child_structure_node_count / two_child_node_count / answer_only / sample 2863496891276065

- `instance_seed`: `2863496891276065`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Find every node with two children. How many are there?
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__binary_tree__depth_level_node_count / single / answer_and_annotation / sample 417271593754678

- `instance_seed`: `417271593754678`
- `word_count`: `78`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. What is the number of nodes on depth level 4?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node at depth 4; use [] when the answer is zero.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[180,148],[495,455]],"answer":2}
```

### task_graph__binary_tree__depth_level_node_count / single / answer_only / sample 417271593754678

- `instance_seed`: `417271593754678`
- `word_count`: `45`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. What is the number of nodes on depth level 4?
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__binary_tree__heap_property_violation_label / single / answer_and_annotation / sample 4026563061131718

- `instance_seed`: `4026563061131718`
- `word_count`: `82`
- `body_word_count`: `31`

```text
This diagram shows a numeric-key binary tree intended to be a min-heap. The tree is intended to be a min-heap except for one parent-child violation. What is the violating child label?
Answer format: set "answer" to the answer node key as a string exactly as shown.
Annotation format: set "annotation" to a JSON object with keys "parent" and "child"; each value is a [x,y] pixel point at that node center.
Example JSON:
{"annotation":{"parent":[180,148],"child":[274,274]},"answer":"42"}
```

### task_graph__binary_tree__heap_property_violation_label / single / answer_only / sample 4026563061131718

- `instance_seed`: `4026563061131718`
- `word_count`: `51`
- `body_word_count`: `31`

```text
This diagram shows a numeric-key binary tree intended to be a min-heap. The tree is intended to be a min-heap except for one parent-child violation. What is the violating child label?
Required answer format: set "answer" to the answer node key as a string exactly as shown.
Example JSON:
{"answer":"42"}
```

### task_graph__binary_tree__local_relative_node_label / left_child_label / answer_and_annotation / sample 5876797510670361

- `instance_seed`: `5876797510670361`
- `word_count`: `81`
- `body_word_count`: `29`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. What label is on the child below-left of 1?
Annotation format: set "annotation" to a JSON object with keys "parent" and "left_child"; each value is a [x,y] pixel point at that node center.
Required answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"parent":[180,148],"left_child":[495,455]},"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / left_child_label / answer_only / sample 5876797510670361

- `instance_seed`: `5876797510670361`
- `word_count`: `49`
- `body_word_count`: `29`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. What label is on the child below-left of 1?
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / parent_label / answer_and_annotation / sample 413196834686146

- `instance_seed`: `413196834686146`
- `word_count`: `82`
- `body_word_count`: `30`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. What is the label of the parent of node "Paa"?
Annotation format: set "annotation" to a JSON object with keys "child" and "parent"; each value is a [x,y] pixel point at that node center.
Required answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"child":[180,148],"parent":[495,455]},"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / parent_label / answer_only / sample 413196834686146

- `instance_seed`: `413196834686146`
- `word_count`: `49`
- `body_word_count`: `45`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. What is the label of the parent of node "Paa"?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / right_child_label / answer_and_annotation / sample 489385827545175

- `instance_seed`: `489385827545175`
- `word_count`: `83`
- `body_word_count`: `31`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. What is the label of the right child of node "KHC"?
Annotation format: set "annotation" to a JSON object with keys "parent" and "right_child"; each value is a [x,y] pixel point at that node center.
Required answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"parent":[180,148],"right_child":[495,455]},"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / right_child_label / answer_only / sample 489385827545175

- `instance_seed`: `489385827545175`
- `word_count`: `50`
- `body_word_count`: `31`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. What is the label of the right child of node "KHC"?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / sibling_label / answer_and_annotation / sample 5655094352767905

- `instance_seed`: `5655094352767905`
- `word_count`: `84`
- `body_word_count`: `30`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Find node 2's sibling. What label does that sibling have?
Annotation format: set "annotation" to a JSON object with keys "node" and "sibling"; each value is a [x,y] pixel point at that node center.
Format for the "answer" field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"node":[180,148],"sibling":[495,455]},"answer":"M"}
```

### task_graph__binary_tree__local_relative_node_label / sibling_label / answer_only / sample 5655094352767905

- `instance_seed`: `5655094352767905`
- `word_count`: `50`
- `body_word_count`: `30`

```text
This diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Find node 2's sibling. What label does that sibling have?
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__lowest_common_ancestor_label / single / answer_and_annotation / sample 6370444253482048

- `instance_seed`: `6370444253482048`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. For nodes "Era" and "Ubs", what label is on their deepest shared ancestor?
Annotation format: set "annotation" to a JSON object with keys "node_a", "node_b", and "lowest_common_ancestor"; each value is a [x,y] pixel point at that node center.
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":{"node_a":[180,148],"node_b":[495,455],"lowest_common_ancestor":[274,274]},"answer":"M"}
```

### task_graph__binary_tree__lowest_common_ancestor_label / single / answer_only / sample 6370444253482048

- `instance_seed`: `6370444253482048`
- `word_count`: `52`
- `body_word_count`: `33`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. For nodes "Era" and "Ubs", what label is on their deepest shared ancestor?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / inorder_kth_node_label / answer_and_annotation / sample 2828588934481952

- `instance_seed`: `2828588934481952`
- `word_count`: `87`
- `body_word_count`: `30`

```text
The diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Using inorder order, what label is visited at position 9?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the inorder traversal nodes from the first visited node through the answer node.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / inorder_kth_node_label / answer_only / sample 2828588934481952

- `instance_seed`: `2828588934481952`
- `word_count`: `49`
- `body_word_count`: `30`

```text
The diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Using inorder order, what label is visited at position 9?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / level_order_kth_node_label / answer_and_annotation / sample 4731498538500545

- `instance_seed`: `4731498538500545`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Traverse the tree level by level from top to bottom and left to right. What label is at position 2?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the level-order traversal nodes from the first visited node through the answer node.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / level_order_kth_node_label / answer_only / sample 4731498538500545

- `instance_seed`: `4731498538500545`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The figure shows a labeled binary tree with the root at the top and left/right children shown by position. Traverse the tree level by level from top to bottom and left to right. What label is at position 2?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / postorder_kth_node_label / answer_and_annotation / sample 5228585366884689

- `instance_seed`: `5228585366884689`
- `word_count`: `87`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. In postorder traversal, which node label is at position 10?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the postorder traversal nodes from the first visited node through the answer node.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / postorder_kth_node_label / answer_only / sample 5228585366884689

- `instance_seed`: `5228585366884689`
- `word_count`: `50`
- `body_word_count`: `30`

```text
The visual shows a labeled binary tree with the root at the top and left/right children shown by position. In postorder traversal, which node label is at position 10?
Required answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / preorder_kth_node_label / answer_and_annotation / sample 4269638941287360

- `instance_seed`: `4269638941287360`
- `word_count`: `89`
- `body_word_count`: `31`

```text
The diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Counting preorder visits from 1, what label appears at position 4?
Annotation format: set "annotation" to an ordered JSON array of [x,y] pixel points at node centers for the preorder traversal nodes from the first visited node through the answer node.
Final answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":[[180,148],[274,274],[495,455]],"answer":"M"}
```

### task_graph__binary_tree__traversal_kth_label / preorder_kth_node_label / answer_only / sample 4269638941287360

- `instance_seed`: `4269638941287360`
- `word_count`: `50`
- `body_word_count`: `31`

```text
The diagram shows a labeled binary tree with the root at the top and left/right children shown by position. Counting preorder visits from 1, what label appears at position 4?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"M"}
```

### task_graph__flow_network__max_flow_value / single / answer_and_annotation / sample 4603383199440900

- `instance_seed`: `4603383199440900`
- `word_count`: `101`
- `body_word_count`: `32`

```text
You are shown a directed capacity network with source S and sink T. What is the largest total flow that can be sent from S to T without exceeding any edge capacity?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a node center of one directed edge in a minimum S-T cut supporting the max-flow value.
Required answer format: set "answer" to the maximum flow value as an integer.
Example JSON:
{"annotation":[[[170,280],[330,210]],[[170,280],[330,350]]],"answer":5}
```

### task_graph__flow_network__max_flow_value / single / answer_only / sample 4603383199440900

- `instance_seed`: `4603383199440900`
- `word_count`: `48`
- `body_word_count`: `44`

```text
You are shown a directed capacity network with source S and sink T. What is the largest total flow that can be sent from S to T without exceeding any edge capacity?
Answer field: set "answer" to the maximum flow value as an integer.
Example JSON:
{"answer":5}
```

### task_graph__flow_network__min_cut_edge_count / single / answer_and_annotation / sample 3887705864169145

- `instance_seed`: `3887705864169145`
- `word_count`: `99`
- `body_word_count`: `28`

```text
The visual shows a directed capacity network with source S and sink T. What is the number of directed edges in the minimum-capacity cut from S to T?
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a node center of one directed edge in the unique minimum S-T cut.
Answer format: set "answer" to the number of directed edges in the unique minimum S-T cut as an integer.
Example JSON:
{"annotation":[[[170,280],[330,210]],[[170,280],[330,350]]],"answer":2}
```

### task_graph__flow_network__min_cut_edge_count / single / answer_only / sample 3887705864169145

- `instance_seed`: `3887705864169145`
- `word_count`: `52`
- `body_word_count`: `28`

```text
The visual shows a directed capacity network with source S and sink T. What is the number of directed edges in the minimum-capacity cut from S to T?
Required answer format: set "answer" to the number of directed edges in the unique minimum S-T cut as an integer.
Example JSON:
{"answer":2}
```

### task_graph__graph_options__contained_subgraph_label / single / answer_and_annotation / sample 4498587335211253

- `instance_seed`: `4498587335211253`
- `word_count`: `65`
- `body_word_count`: `26`

```text
The figure shows a Target Graph above four labeled directed-graph options; arrow directions matter. Which option is contained in the Target Graph as a labeled subgraph?
Answer format: set "answer" to the exact option letter of the correct graph.
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected option panel.
Example JSON:
{"annotation":[472,520,828,742],"answer":"D"}
```

### task_graph__graph_options__contained_subgraph_label / single / answer_only / sample 4498587335211253

- `instance_seed`: `4498587335211253`
- `word_count`: `44`
- `body_word_count`: `26`

```text
The figure shows a Target Graph above four labeled directed-graph options; arrow directions matter. Which option is contained in the Target Graph as a labeled subgraph?
Final answer format: set "answer" to the exact option letter of the correct graph.
Example JSON:
{"answer":"D"}
```

### task_graph__graph_options__same_structure_label / single / answer_and_annotation / sample 585610358376055

- `instance_seed`: `585610358376055`
- `word_count`: `67`
- `body_word_count`: `26`

```text
The figure shows a Reference labeled directed graph above four labeled directed-graph options; arrow directions matter. Which labeled option represents the same graph as the Reference?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected option panel.
Required answer format: set "answer" to the exact option letter of the correct graph.
Example JSON:
{"annotation":[472,520,828,742],"answer":"D"}
```

### task_graph__graph_options__same_structure_label / single / answer_only / sample 585610358376055

- `instance_seed`: `585610358376055`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The figure shows a Reference labeled directed graph above four labeled directed-graph options; arrow directions matter. Which labeled option represents the same graph as the Reference?
Answer format: set "answer" to the exact option letter of the correct graph.
Example JSON:
{"answer":"D"}
```

### task_graph__metro__exact_distance_station_count / single / answer_and_annotation / sample 310556150842228

- `instance_seed`: `310556150842228`
- `word_count`: `79`
- `body_word_count`: `27`

```text
The image shows a labeled metro route map with colored routes and stations. How many stations have shortest metro-route distance exactly 2 route segments from station 6?
Final answer format: set "answer" to the requested count or length as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all stations whose shortest metro-route distance from 6 is exactly 2 route segments.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__exact_distance_station_count / single / answer_only / sample 310556150842228

- `instance_seed`: `310556150842228`
- `word_count`: `45`
- `body_word_count`: `27`

```text
The image shows a labeled metro route map with colored routes and stations. How many stations have shortest metro-route distance exactly 2 route segments from station 6?
Final answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__metro__route_condition_station_count / metro_route_single_route_station_count / answer_and_annotation / sample 7317405745901232

- `instance_seed`: `7317405745901232`
- `word_count`: `68`
- `body_word_count`: `21`

```text
The image shows a labeled metro route map with colored routes and stations. Count the non-transfer stations on the Orange route.
Final answer format: set "answer" to the requested count or length as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all stations served only by the Orange route.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__route_condition_station_count / metro_route_single_route_station_count / answer_only / sample 7317405745901232

- `instance_seed`: `7317405745901232`
- `word_count`: `41`
- `body_word_count`: `21`

```text
The image shows a labeled metro route map with colored routes and stations. Count the non-transfer stations on the Orange route.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__metro__route_condition_station_count / metro_route_transfer_station_count / answer_and_annotation / sample 8265650205547167

- `instance_seed`: `8265650205547167`
- `word_count`: `76`
- `body_word_count`: `21`

```text
The visual shows a labeled metro route map with colored routes and stations. Count the transfer stations on the Green route.
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all transfer stations on the Green route; use an empty array when there are none.
Required answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__route_condition_station_count / metro_route_transfer_station_count / answer_only / sample 8265650205547167

- `instance_seed`: `8265650205547167`
- `word_count`: `39`
- `body_word_count`: `21`

```text
The visual shows a labeled metro route map with colored routes and stations. Count the transfer stations on the Green route.
Final answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__metro__shortest_path_length / single / answer_and_annotation / sample 3609314617225980

- `instance_seed`: `3609314617225980`
- `word_count`: `91`
- `body_word_count`: `36`

```text
You are shown a labeled metro route map with colored routes and stations. The metro map has a unique shortest station path from station P to station L. How many route segments are in that path?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at station centers along the unique shortest path from P to L, excluding P and including L.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__shortest_path_length / single / answer_only / sample 3609314617225980

- `instance_seed`: `3609314617225980`
- `word_count`: `54`
- `body_word_count`: `36`

```text
You are shown a labeled metro route map with colored routes and stations. The metro map has a unique shortest station path from station P to station L. How many route segments are in that path?
Final answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__metro__station_membership_count / metro_single_route_station_count / answer_and_annotation / sample 2611942225094606

- `instance_seed`: `2611942225094606`
- `word_count`: `73`
- `body_word_count`: `26`

```text
The figure shows a labeled metro route map with colored routes and stations. What is the number of stations with exactly one route passing through them?
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all stations served by exactly one route.
Required answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__station_membership_count / metro_single_route_station_count / answer_only / sample 2611942225094606

- `instance_seed`: `2611942225094606`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The figure shows a labeled metro route map with colored routes and stations. What is the number of stations with exactly one route passing through them?
Answer field: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__metro__station_membership_count / metro_transfer_station_count / answer_and_annotation / sample 1473923941147511

- `instance_seed`: `1473923941147511`
- `word_count`: `67`
- `body_word_count`: `26`

```text
The visual shows a labeled metro route map with colored routes and stations. What is the number of stations shared by two or more colored routes?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all transfer stations.
Answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__metro__station_membership_count / metro_transfer_station_count / answer_only / sample 1473923941147511

- `instance_seed`: `1473923941147511`
- `word_count`: `46`
- `body_word_count`: `26`

```text
The visual shows a labeled metro route map with colored routes and stations. What is the number of stations shared by two or more colored routes?
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__articulation_point_count / single / answer_and_annotation / sample 1656114560650368

- `instance_seed`: `1656114560650368`
- `word_count`: `58`
- `body_word_count`: `17`

```text
The diagram shows a labeled undirected graph. What is the number of articulation points in the graph?
Answer format: set "answer" to the count of articulation-point nodes as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all articulation-point nodes.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__articulation_point_count / single / answer_only / sample 1656114560650368

- `instance_seed`: `1656114560650368`
- `word_count`: `35`
- `body_word_count`: `17`

```text
The diagram shows a labeled undirected graph. What is the number of articulation points in the graph?
Required answer format: set "answer" to the count of articulation-point nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__bridge_count / single / answer_and_annotation / sample 7552016354717619

- `instance_seed`: `7552016354717619`
- `word_count`: `80`
- `body_word_count`: `18`

```text
The diagram shows a labeled undirected graph. How many edges would disconnect part of the graph if removed?
Answer format: set "answer" to the count of bridge edges as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of a bridge edge.
Example JSON:
{"annotation":[[[180,220],[310,180]],[[310,180],[430,260]]],"answer":2}
```

### task_graph__node_link__bridge_count / single / answer_only / sample 7552016354717619

- `instance_seed`: `7552016354717619`
- `word_count`: `36`
- `body_word_count`: `18`

```text
The diagram shows a labeled undirected graph. How many edges would disconnect part of the graph if removed?
Required answer format: set "answer" to the count of bridge edges as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__common_related_node_count / directed_common_predecessor_count / answer_and_annotation / sample 8964778421036150

- `instance_seed`: `8964778421036150`
- `word_count`: `84`
- `body_word_count`: `24`

```text
The figure shows a labeled directed graph. Find the nodes that send arrows to both node 7 and node 6. How many are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node that points directly to both 7 and 6; use an empty array when the answer is zero.
Format for the "answer" field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__common_related_node_count / directed_common_predecessor_count / answer_only / sample 8964778421036150

- `instance_seed`: `8964778421036150`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The figure shows a labeled directed graph. Find the nodes that send arrows to both node 7 and node 6. How many are there?
Answer field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__common_related_node_count / directed_common_successor_count / answer_and_annotation / sample 8544789415982312

- `instance_seed`: `8544789415982312`
- `word_count`: `81`
- `body_word_count`: `23`

```text
The figure shows a labeled directed graph. What is the number of nodes that both node "OPK" and node "NVA" point to directly?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node that both "OPK" and "NVA" point to directly; use an empty array when the answer is zero.
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__common_related_node_count / directed_common_successor_count / answer_only / sample 8544789415982312

- `instance_seed`: `8544789415982312`
- `word_count`: `41`
- `body_word_count`: `23`

```text
The figure shows a labeled directed graph. What is the number of nodes that both node "OPK" and node "NVA" point to directly?
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__common_related_node_count / undirected_common_neighbor_count / answer_and_annotation / sample 3691274619738162

- `instance_seed`: `3691274619738162`
- `word_count`: `75`
- `body_word_count`: `19`

```text
The figure shows a labeled undirected graph. How many shared neighboring nodes do node "Day" and node "Had" have?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of every node directly connected to both "Day" and "Had"; use an empty array when the answer is zero.
Answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__common_related_node_count / undirected_common_neighbor_count / answer_only / sample 3691274619738162

- `instance_seed`: `3691274619738162`
- `word_count`: `37`
- `body_word_count`: `19`

```text
The figure shows a labeled undirected graph. How many shared neighboring nodes do node "Day" and node "Had" have?
Final answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / component_size_after_edge_addition / answer_and_annotation / sample 5786724094523424

- `instance_seed`: `5786724094523424`
- `word_count`: `94`
- `body_word_count`: `34`

```text
The image shows a labeled undirected graph. If an edge were added between node C and node Q, how many nodes, including node Q itself, would be in the same connected component as Q?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be in the same connected component as Q after adding an edge between C and Q, including Q.
Answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / component_size_after_edge_addition / answer_only / sample 5786724094523424

- `instance_seed`: `5786724094523424`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The image shows a labeled undirected graph. If an edge were added between node C and node Q, how many nodes, including node Q itself, would be in the same connected component as Q?
Answer field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / component_size_after_edge_removal / answer_and_annotation / sample 2974971322339970

- `instance_seed`: `2974971322339970`
- `word_count`: `92`
- `body_word_count`: `29`

```text
The image shows a labeled undirected graph. Imagine deleting the edge between node K and node V. How many labeled nodes would remain connected to node K, including K?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be in the same connected component as K after removing the edge between K and V, including K.
Format for the "answer" field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__component_size_after_edge_edit / component_size_after_edge_removal / answer_only / sample 2974971322339970

- `instance_seed`: `2974971322339970`
- `word_count`: `46`
- `body_word_count`: `42`

```text
The image shows a labeled undirected graph. Imagine deleting the edge between node K and node V. How many labeled nodes would remain connected to node K, including K?
Answer field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__cross_color_edge_count / cross_color_edge_count / answer_and_annotation / sample 5193411690173881

- `instance_seed`: `5193411690173881`
- `word_count`: `96`
- `body_word_count`: `23`

```text
The diagram shows a labeled undirected graph with colored nodes. Count the edges whose endpoint nodes are colored cyan [#34C4E0] and purple [#963ACA].
Answer format: set "answer" to the count of matching edges as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge connecting a cyan [#34C4E0] node and a purple [#963ACA] node; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__cross_color_edge_count / cross_color_edge_count / answer_only / sample 5193411690173881

- `instance_seed`: `5193411690173881`
- `word_count`: `41`
- `body_word_count`: `23`

```text
The diagram shows a labeled undirected graph with colored nodes. Count the edges whose endpoint nodes are colored cyan [#34C4E0] and purple [#963ACA].
Final answer format: set "answer" to the count of matching edges as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__cross_color_edge_count / directed_cross_color_edge_count / answer_and_annotation / sample 6726574745274512

- `instance_seed`: `6726574745274512`
- `word_count`: `98`
- `body_word_count`: `24`

```text
The image shows a labeled directed graph with colored nodes. How many arrows go from a maroon [#963644] node to a red [#E63232] node?
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the source or target node center for one arrow from a maroon [#963644] node to a red [#E63232] node; use [] when the answer is zero.
Required answer format: set "answer" to the count of matching edges as an integer.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__cross_color_edge_count / directed_cross_color_edge_count / answer_only / sample 6726574745274512

- `instance_seed`: `6726574745274512`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The image shows a labeled directed graph with colored nodes. How many arrows go from a maroon [#963644] node to a red [#E63232] node?
Answer field: set "answer" to the count of matching edges as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / directed_in_degree_one_filter_remaining_count / answer_and_annotation / sample 3859090740806284

- `instance_seed`: `3859090740806284`
- `word_count`: `85`
- `body_word_count`: `23`

```text
This diagram shows a labeled directed graph. Exclude every node that receives exactly one directed edge. What is the number of remaining nodes?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would remain after removing every node with in-degree 1; use an empty array when the answer is zero.
Format for the "answer" field: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / directed_in_degree_one_filter_remaining_count / answer_only / sample 3859090740806284

- `instance_seed`: `3859090740806284`
- `word_count`: `40`
- `body_word_count`: `23`

```text
This diagram shows a labeled directed graph. Exclude every node that receives exactly one directed edge. What is the number of remaining nodes?
Answer format: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / directed_out_degree_one_filter_remaining_count / answer_and_annotation / sample 8153532359983396

- `instance_seed`: `8153532359983396`
- `word_count`: `80`
- `body_word_count`: `21`

```text
The visual shows a labeled directed graph. After filtering out the nodes whose out-degree is 1, how many labeled nodes remain?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would remain after removing every node with out-degree 1; use an empty array when the answer is zero.
Answer format: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / directed_out_degree_one_filter_remaining_count / answer_only / sample 8153532359983396

- `instance_seed`: `8153532359983396`
- `word_count`: `38`
- `body_word_count`: `21`

```text
The visual shows a labeled directed graph. After filtering out the nodes whose out-degree is 1, how many labeled nodes remain?
Answer format: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / undirected_degree_one_filter_remaining_count / answer_and_annotation / sample 8675337062488204

- `instance_seed`: `8675337062488204`
- `word_count`: `80`
- `body_word_count`: `21`

```text
The image shows a labeled undirected graph. Exclude every node whose degree is 1. What is the number of remaining nodes?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would remain after removing every node with degree 1; use an empty array when the answer is zero.
Answer format: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_after_removal_filter_count / undirected_degree_one_filter_remaining_count / answer_only / sample 8675337062488204

- `instance_seed`: `8675337062488204`
- `word_count`: `38`
- `body_word_count`: `34`

```text
The image shows a labeled undirected graph. Exclude every node whose degree is 1. What is the number of remaining nodes?
Answer field: set "answer" to the count of remaining nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_extremum_value / directed_max_in_degree_value / answer_and_annotation / sample 2330581199396414

- `instance_seed`: `2330581199396414`
- `word_count`: `60`
- `body_word_count`: `15`

```text
The visual shows a labeled directed graph. Find the maximum in-degree in the directed graph.
Answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the node whose in-degree equals the maximum in-degree value.
Example JSON:
{"annotation":[180,220],"answer":3}
```

### task_graph__node_link__degree_extremum_value / directed_max_in_degree_value / answer_only / sample 2330581199396414

- `instance_seed`: `2330581199396414`
- `word_count`: `35`
- `body_word_count`: `15`

```text
The visual shows a labeled directed graph. Find the maximum in-degree in the directed graph.
Required answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"answer":3}
```

### task_graph__node_link__degree_extremum_value / directed_max_out_degree_value / answer_and_annotation / sample 3697736993399073

- `instance_seed`: `3697736993399073`
- `word_count`: `65`
- `body_word_count`: `19`

```text
This diagram shows a labeled directed graph. What is the maximum number of directed edges starting at any node?
Final answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the node whose out-degree equals the maximum out-degree value.
Example JSON:
{"annotation":[180,220],"answer":3}
```

### task_graph__node_link__degree_extremum_value / directed_max_out_degree_value / answer_only / sample 3697736993399073

- `instance_seed`: `3697736993399073`
- `word_count`: `38`
- `body_word_count`: `19`

```text
This diagram shows a labeled directed graph. What is the maximum number of directed edges starting at any node?
Answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"answer":3}
```

### task_graph__node_link__degree_extremum_value / undirected_max_degree_value / answer_and_annotation / sample 3444012320566096

- `instance_seed`: `3444012320566096`
- `word_count`: `61`
- `body_word_count`: `15`

```text
This diagram shows a labeled undirected graph. Find the maximum node degree in the graph.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the node whose degree equals the maximum degree value.
Required answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"annotation":[180,220],"answer":3}
```

### task_graph__node_link__degree_extremum_value / undirected_max_degree_value / answer_only / sample 3444012320566096

- `instance_seed`: `3444012320566096`
- `word_count`: `34`
- `body_word_count`: `30`

```text
This diagram shows a labeled undirected graph. Find the maximum node degree in the graph.
Answer field: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"answer":3}
```

### task_graph__node_link__degree_extremum_value / undirected_min_degree_value / answer_and_annotation / sample 5430034111217970

- `instance_seed`: `5430034111217970`
- `word_count`: `63`
- `body_word_count`: `15`

```text
The diagram shows a labeled undirected graph. Find the minimum node degree in the graph.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the node whose degree equals the minimum degree value.
Format for the "answer" field: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"annotation":[180,220],"answer":3}
```

### task_graph__node_link__degree_extremum_value / undirected_min_degree_value / answer_only / sample 5430034111217970

- `instance_seed`: `5430034111217970`
- `word_count`: `35`
- `body_word_count`: `15`

```text
The diagram shows a labeled undirected graph. Find the minimum node degree in the graph.
Final answer format: set "answer" to the requested maximum or minimum degree value as an integer.
Example JSON:
{"answer":3}
```

### task_graph__node_link__degree_value_filter_count / directed_in_degree_count / answer_and_annotation / sample 3930545007477223

- `instance_seed`: `3930545007477223`
- `word_count`: `62`
- `body_word_count`: `13`

```text
The visual shows a labeled directed graph. How many nodes have in-degree 2?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes with in-degree 2; use an empty array when the answer is zero.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_value_filter_count / directed_in_degree_count / answer_only / sample 3930545007477223

- `instance_seed`: `3930545007477223`
- `word_count`: `30`
- `body_word_count`: `13`

```text
The visual shows a labeled directed graph. How many nodes have in-degree 2?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_value_filter_count / directed_out_degree_count / answer_and_annotation / sample 4917000487141535

- `instance_seed`: `4917000487141535`
- `word_count`: `69`
- `body_word_count`: `17`

```text
This diagram shows a labeled directed graph. Find all nodes with out-degree 4. How many are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes with out-degree 4; use an empty array when the answer is zero.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_value_filter_count / directed_out_degree_count / answer_only / sample 4917000487141535

- `instance_seed`: `4917000487141535`
- `word_count`: `31`
- `body_word_count`: `17`

```text
This diagram shows a labeled directed graph. Find all nodes with out-degree 4. How many are there?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__degree_value_filter_count / undirected_degree_count / answer_and_annotation / sample 2899664470998672

- `instance_seed`: `2899664470998672`
- `word_count`: `62`
- `body_word_count`: `13`

```text
The figure shows a labeled undirected graph. How many nodes have degree 3?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes with degree 3; use an empty array when the answer is zero.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__degree_value_filter_count / undirected_degree_count / answer_only / sample 2899664470998672

- `instance_seed`: `2899664470998672`
- `word_count`: `30`
- `body_word_count`: `13`

```text
The figure shows a labeled undirected graph. How many nodes have degree 3?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__edge_between_nodes_label / directed_edge_between_nodes_label / answer_and_annotation / sample 8716541533233809

- `instance_seed`: `8716541533233809`
- `word_count`: `75`
- `body_word_count`: `27`

```text
This diagram shows a directed graph with text labels on its arrows. What is the visible label attached to the arrow from node "Shu" to node "Ati"?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the visible text label on the arrow from "Shu" to "Ati".
Format for the "answer" field: set "answer" to that edge label as a lowercase string.
Example JSON:
{"annotation":[180,220,230,245],"answer":"alpha"}
```

### task_graph__node_link__edge_between_nodes_label / directed_edge_between_nodes_label / answer_only / sample 8716541533233809

- `instance_seed`: `8716541533233809`
- `word_count`: `43`
- `body_word_count`: `27`

```text
This diagram shows a directed graph with text labels on its arrows. What is the visible label attached to the arrow from node "Shu" to node "Ati"?
Answer format: set "answer" to that edge label as a lowercase string.
Example JSON:
{"answer":"alpha"}
```

### task_graph__node_link__edge_between_nodes_label / edge_between_nodes_label / answer_and_annotation / sample 7482657018709047

- `instance_seed`: `7482657018709047`
- `word_count`: `71`
- `body_word_count`: `25`

```text
This diagram shows a graph with text labels on its edges. Read the edge connecting node 3 and node 5. What label is on it?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the visible text label on the edge between 3 and 5.
Required answer format: set "answer" to that edge label as a lowercase string.
Example JSON:
{"annotation":[180,220,230,245],"answer":"alpha"}
```

### task_graph__node_link__edge_between_nodes_label / edge_between_nodes_label / answer_only / sample 7482657018709047

- `instance_seed`: `7482657018709047`
- `word_count`: `44`
- `body_word_count`: `25`

```text
This diagram shows a graph with text labels on its edges. Read the edge connecting node 3 and node 5. What label is on it?
Format for the "answer" field: set "answer" to that edge label as a lowercase string.
Example JSON:
{"answer":"alpha"}
```

### task_graph__node_link__edge_color_count / single / answer_and_annotation / sample 4580126231793567

- `instance_seed`: `4580126231793567`
- `word_count`: `93`
- `body_word_count`: `17`

```text
The image shows a labeled undirected graph with colored edges. How many edges are colored cyan [#34C4E0]?
Answer format: set "answer" to the count of matching edges as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge colored cyan [#34C4E0]; for directed graphs, use the source and target node centers; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__edge_color_count / single / answer_only / sample 4580126231793567

- `instance_seed`: `4580126231793567`
- `word_count`: `34`
- `body_word_count`: `30`

```text
The image shows a labeled undirected graph with colored edges. How many edges are colored cyan [#34C4E0]?
Answer field: set "answer" to the count of matching edges as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__edge_text_count / single / answer_and_annotation / sample 1600201514519221

- `instance_seed`: `1600201514519221`
- `word_count`: `72`
- `body_word_count`: `22`

```text
The image shows a labeled undirected graph with visible boxed text labels on its edges. How many visible edge labels read "crauy"?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around every visible edge-label text box that reads "crauy".
Answer format: set "answer" to the count of matching edge labels as an integer.
Example JSON:
{"annotation":[[248,190,300,214],[420,238,472,262]],"answer":2}
```

### task_graph__node_link__edge_text_count / single / answer_only / sample 1600201514519221

- `instance_seed`: `1600201514519221`
- `word_count`: `43`
- `body_word_count`: `22`

```text
The image shows a labeled undirected graph with visible boxed text labels on its edges. How many visible edge labels read "crauy"?
Format for the "answer" field: set "answer" to the count of matching edge labels as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__hamiltonian_cycle_neighbor_label / next_in_hamiltonian_cycle_label / answer_and_annotation / sample 8355519752979234

- `instance_seed`: `8355519752979234`
- `word_count`: `79`
- `body_word_count`: `40`

```text
The figure shows a labeled undirected graph with exactly one Hamiltonian cycle. Start at K and move around the Hamiltonian cycle so that Y is last before returning to the start. What node is immediately after K along that cycle?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the answer node.
Required answer format: set "answer" to the label of the requested node as a string.
Example JSON:
{"annotation":[310,180],"answer":"B"}
```

### task_graph__node_link__hamiltonian_cycle_neighbor_label / next_in_hamiltonian_cycle_label / answer_only / sample 8355519752979234

- `instance_seed`: `8355519752979234`
- `word_count`: `59`
- `body_word_count`: `40`

```text
The figure shows a labeled undirected graph with exactly one Hamiltonian cycle. Start at K and move around the Hamiltonian cycle so that Y is last before returning to the start. What node is immediately after K along that cycle?
Final answer format: set "answer" to the label of the requested node as a string.
Example JSON:
{"answer":"B"}
```

### task_graph__node_link__hamiltonian_cycle_neighbor_label / previous_in_hamiltonian_cycle_label / answer_and_annotation / sample 3453772839096100

- `instance_seed`: `3453772839096100`
- `word_count`: `73`
- `body_word_count`: `35`

```text
This diagram shows a labeled undirected graph with exactly one Hamiltonian cycle. With "Uli" as the first cycle node and "Nev" as the final node before returning, which node precedes "Nev" along the Hamiltonian cycle?
Answer format: set "answer" to the label of the requested node as a string.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the answer node.
Example JSON:
{"annotation":[310,180],"answer":"B"}
```

### task_graph__node_link__hamiltonian_cycle_neighbor_label / previous_in_hamiltonian_cycle_label / answer_only / sample 3453772839096100

- `instance_seed`: `3453772839096100`
- `word_count`: `53`
- `body_word_count`: `35`

```text
This diagram shows a labeled undirected graph with exactly one Hamiltonian cycle. With "Uli" as the first cycle node and "Nev" as the final node before returning, which node precedes "Nev" along the Hamiltonian cycle?
Answer format: set "answer" to the label of the requested node as a string.
Example JSON:
{"answer":"B"}
```

### task_graph__node_link__isolated_after_removal_count / single / answer_and_annotation / sample 1420120087924769

- `instance_seed`: `1420120087924769`
- `word_count`: `78`
- `body_word_count`: `19`

```text
The visual shows a labeled undirected graph. After removing node "Fyn", how many nodes would have no connections left?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all remaining nodes that would be isolated after removing "Fyn"; use an empty array when the answer is zero.
Answer format: set "answer" to the count of those remaining isolated nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__isolated_after_removal_count / single / answer_only / sample 1420120087924769

- `instance_seed`: `1420120087924769`
- `word_count`: `39`
- `body_word_count`: `19`

```text
The visual shows a labeled undirected graph. After removing node "Fyn", how many nodes would have no connections left?
Final answer format: set "answer" to the count of those remaining isolated nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__largest_chordless_cycle_size / single / answer_and_annotation / sample 5071633831097522

- `instance_seed`: `5071633831097522`
- `word_count`: `87`
- `body_word_count`: `31`

```text
The visual shows a labeled undirected graph with several cycles. Find the largest chordless cycle, meaning a cycle with no chords between non-adjacent cycle nodes. How many nodes does it contain?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes in one largest chordless cycle; order does not matter.
Format for the "answer" field: set "answer" to the number of nodes in that largest chordless cycle as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__largest_chordless_cycle_size / single / answer_only / sample 5071633831097522

- `instance_seed`: `5071633831097522`
- `word_count`: `52`
- `body_word_count`: `31`

```text
The visual shows a labeled undirected graph with several cycles. Find the largest chordless cycle, meaning a cycle with no chords between non-adjacent cycle nodes. How many nodes does it contain?
Answer format: set "answer" to the number of nodes in that largest chordless cycle as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__largest_component_size / single / answer_and_annotation / sample 698642285522490

- `instance_seed`: `698642285522490`
- `word_count`: `66`
- `body_word_count`: `18`

```text
This diagram shows a labeled undirected graph. Find the largest connected component. How many nodes does it contain?
Answer format: set "answer" to the number of nodes in that component as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes in the unique largest connected component.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__largest_component_size / single / answer_only / sample 698642285522490

- `instance_seed`: `698642285522490`
- `word_count`: `40`
- `body_word_count`: `18`

```text
This diagram shows a labeled undirected graph. Find the largest connected component. How many nodes does it contain?
Format for the "answer" field: set "answer" to the number of nodes in that component as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__longest_path_length / single / answer_and_annotation / sample 6737445764907440

- `instance_seed`: `6737445764907440`
- `word_count`: `86`
- `body_word_count`: `28`

```text
The visual shows a labeled directed acyclic graph. Among all arrow-following paths in the directed acyclic graph, the longest one is unique. How many edges are on it?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at node centers along the unique longest directed path, from its start node to its end node.
Format for the "answer" field: set "answer" to the number of directed edges in that path as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__longest_path_length / single / answer_only / sample 6737445764907440

- `instance_seed`: `6737445764907440`
- `word_count`: `51`
- `body_word_count`: `28`

```text
The visual shows a labeled directed acyclic graph. Among all arrow-following paths in the directed acyclic graph, the longest one is unique. How many edges are on it?
Format for the "answer" field: set "answer" to the number of directed edges in that path as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__mst_weight / single / answer_and_annotation / sample 680873991491731

- `instance_seed`: `680873991491731`
- `word_count`: `103`
- `body_word_count`: `37`

```text
This diagram shows a labeled connected weighted graph. A spanning tree uses edges to connect all nodes and has no cycles. Among those trees, the minimum-weight one is unique. What is the sum of its edge weights?
Final answer format: set "answer" to the total weight of that minimum spanning tree as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge in the minimum spanning tree.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__mst_weight / single / answer_only / sample 680873991491731

- `instance_seed`: `680873991491731`
- `word_count`: `58`
- `body_word_count`: `37`

```text
This diagram shows a labeled connected weighted graph. A spanning tree uses edges to connect all nodes and has no cycles. Among those trees, the minimum-weight one is unique. What is the sum of its edge weights?
Required answer format: set "answer" to the total weight of that minimum spanning tree as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_in_degree_value / answer_and_annotation / sample 3338412421099513

- `instance_seed`: `3338412421099513`
- `word_count`: `81`
- `body_word_count`: `15`

```text
The image shows a labeled directed graph. Count the incoming directed edges for node J.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the source or target node center for one arrow pointing into node J; use [] when the answer is zero.
Answer format: set "answer" to the queried node degree as an integer.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_in_degree_value / answer_only / sample 3338412421099513

- `instance_seed`: `3338412421099513`
- `word_count`: `34`
- `body_word_count`: `15`

```text
The image shows a labeled directed graph. Count the incoming directed edges for node J.
Format for the "answer" field: set "answer" to the queried node degree as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_out_degree_value / answer_and_annotation / sample 7149716831803351

- `instance_seed`: `7149716831803351`
- `word_count`: `80`
- `body_word_count`: `15`

```text
The diagram shows a labeled directed graph. Count the outgoing directed edges from node "Zia".
Answer format: set "answer" to the queried node degree as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the source or target node center for one arrow leaving node "Zia"; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_out_degree_value / answer_only / sample 7149716831803351

- `instance_seed`: `7149716831803351`
- `word_count`: `31`
- `body_word_count`: `27`

```text
The diagram shows a labeled directed graph. Count the outgoing directed edges from node "Zia".
Answer field: set "answer" to the queried node degree as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_total_degree_value / answer_and_annotation / sample 1020183973914468

- `instance_seed`: `1020183973914468`
- `word_count`: `85`
- `body_word_count`: `19`

```text
The image shows a labeled directed graph. Count all arrows incident to node "Nou". What is its total degree?
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the source or target node center of one arrow touching node "Nou"; use [] when the answer is zero.
Required answer format: set "answer" to the queried node degree as an integer.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__named_node_degree_value / directed_named_node_total_degree_value / answer_only / sample 1020183973914468

- `instance_seed`: `1020183973914468`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The image shows a labeled directed graph. Count all arrows incident to node "Nou". What is its total degree?
Answer field: set "answer" to the queried node degree as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__named_node_degree_value / undirected_named_node_degree_value / answer_and_annotation / sample 1961035860837642

- `instance_seed`: `1961035860837642`
- `word_count`: `79`
- `body_word_count`: `13`

```text
The diagram shows a labeled undirected graph. How many edges touch node Y?
Final answer format: set "answer" to the queried node degree as an integer.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at the center of one endpoint node of an edge touching node Y; use [] when the answer is zero.
Example JSON:
{"annotation":[[[180,220],[310,180]]],"answer":2}
```

### task_graph__node_link__named_node_degree_value / undirected_named_node_degree_value / answer_only / sample 1961035860837642

- `instance_seed`: `1961035860837642`
- `word_count`: `29`
- `body_word_count`: `25`

```text
The diagram shows a labeled undirected graph. How many edges touch node Y?
Answer field: set "answer" to the queried node degree as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__node_color_count / single / answer_and_annotation / sample 85928782173089

- `instance_seed`: `85928782173089`
- `word_count`: `63`
- `body_word_count`: `19`

```text
The figure shows a labeled undirected graph with colored nodes. Find every red [#E63232] node. How many are there?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes colored red [#E63232].
Required answer format: set "answer" to the count of matching nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__node_color_count / single / answer_only / sample 85928782173089

- `instance_seed`: `85928782173089`
- `word_count`: `37`
- `body_word_count`: `19`

```text
The figure shows a labeled undirected graph with colored nodes. Find every red [#E63232] node. How many are there?
Final answer format: set "answer" to the count of matching nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__reachable_count / single / answer_and_annotation / sample 2665606705776448

- `instance_seed`: `2665606705776448`
- `word_count`: `67`
- `body_word_count`: `20`

```text
The image shows a labeled directed graph. From node W, how many other nodes are reachable in the directed graph?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes reachable from W, excluding W itself.
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__reachable_count / single / answer_only / sample 2665606705776448

- `instance_seed`: `2665606705776448`
- `word_count`: `38`
- `body_word_count`: `20`

```text
The image shows a labeled directed graph. From node W, how many other nodes are reachable in the directed graph?
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__reachable_count_after_edge_edit / reachable_count_after_edge_addition / answer_and_annotation / sample 4227700639264708

- `instance_seed`: `4227700639264708`
- `word_count`: `84`
- `body_word_count`: `27`

```text
This diagram shows a labeled directed graph. After adding an arrow from node H to node V, how many nodes could be reached from H, including H?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be reachable from H after adding an arrow from H to V, including H.
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__reachable_count_after_edge_edit / reachable_count_after_edge_addition / answer_only / sample 4227700639264708

- `instance_seed`: `4227700639264708`
- `word_count`: `44`
- `body_word_count`: `40`

```text
This diagram shows a labeled directed graph. After adding an arrow from node H to node V, how many nodes could be reached from H, including H?
Answer field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__reachable_count_after_edge_edit / reachable_count_after_edge_removal / answer_and_annotation / sample 8651274970261045

- `instance_seed`: `8651274970261045`
- `word_count`: `89`
- `body_word_count`: `32`

```text
The figure shows a labeled directed graph. Imagine deleting the directed edge from node "Dux" to node "Bam". How many labeled nodes would remain reachable from "Dux" when arrow directions are followed?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes that would be reachable from "Dux" after removing the arrow from "Dux" to "Bam", including "Dux".
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__reachable_count_after_edge_edit / reachable_count_after_edge_removal / answer_only / sample 8651274970261045

- `instance_seed`: `8651274970261045`
- `word_count`: `52`
- `body_word_count`: `32`

```text
The figure shows a labeled directed graph. Imagine deleting the directed edge from node "Dux" to node "Bam". How many labeled nodes would remain reachable from "Dux" when arrow directions are followed?
Format for the "answer" field: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__same_component_count / single / answer_and_annotation / sample 7042900420123297

- `instance_seed`: `7042900420123297`
- `word_count`: `71`
- `body_word_count`: `18`

```text
The figure shows a labeled undirected graph. How many labeled nodes belong to node "Bnb"'s connected component?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes in the connected component containing the asked node, including the asked node itself.
Answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__same_component_count / single / answer_only / sample 7042900420123297

- `instance_seed`: `7042900420123297`
- `word_count`: `36`
- `body_word_count`: `18`

```text
The figure shows a labeled undirected graph. How many labeled nodes belong to node "Bnb"'s connected component?
Required answer format: set "answer" to the count of those nodes as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__shortest_path_length / directed_shortest_path_length / answer_and_annotation / sample 6179717728097755

- `instance_seed`: `6179717728097755`
- `word_count`: `80`
- `body_word_count`: `19`

```text
This diagram shows a labeled directed graph. What is the directed shortest-path length from node "Ncr" to node "Pro"?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at node centers after node "Ncr" along the unique shortest path to node "Pro" while following arrow directions, ending at "Pro".
Format for the "answer" field: set "answer" to the number of edges in that path as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__shortest_path_length / directed_shortest_path_length / answer_only / sample 6179717728097755

- `instance_seed`: `6179717728097755`
- `word_count`: `38`
- `body_word_count`: `19`

```text
This diagram shows a labeled directed graph. What is the directed shortest-path length from node "Ncr" to node "Pro"?
Answer format: set "answer" to the number of edges in that path as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__shortest_path_length / undirected_shortest_path_length / answer_and_annotation / sample 1729035166682362

- `instance_seed`: `1729035166682362`
- `word_count`: `77`
- `body_word_count`: `22`

```text
This diagram shows a labeled undirected graph. How many edges lie on the unique shortest path from node 10 to node 9?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at node centers after node 10 along the unique shortest path to node 9, ending at 9.
Required answer format: set "answer" to the number of edges in that path as an integer.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__shortest_path_length / undirected_shortest_path_length / answer_only / sample 1729035166682362

- `instance_seed`: `1729035166682362`
- `word_count`: `41`
- `body_word_count`: `22`

```text
This diagram shows a labeled undirected graph. How many edges lie on the unique shortest path from node 10 to node 9?
Answer format: set "answer" to the number of edges in that path as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__topological_endpoint_node_label / first_in_topological_order_label / answer_and_annotation / sample 5903104642679739

- `instance_seed`: `5903104642679739`
- `word_count`: `57`
- `body_word_count`: `17`

```text
The image shows a labeled directed acyclic graph. Which node is first in the unique topological order?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the first node in the unique topological order.
Answer format: set "answer" to that node label as a string.
Example JSON:
{"annotation":[180,160],"answer":"A"}
```

### task_graph__node_link__topological_endpoint_node_label / first_in_topological_order_label / answer_only / sample 5903104642679739

- `instance_seed`: `5903104642679739`
- `word_count`: `32`
- `body_word_count`: `28`

```text
The image shows a labeled directed acyclic graph. Which node is first in the unique topological order?
Answer field: set "answer" to that node label as a string.
Example JSON:
{"answer":"A"}
```

### task_graph__node_link__topological_endpoint_node_label / last_in_topological_order_label / answer_and_annotation / sample 345994588924632

- `instance_seed`: `345994588924632`
- `word_count`: `58`
- `body_word_count`: `18`

```text
This diagram shows a labeled directed acyclic graph. Using the graph's unique topological order, which node comes last?
Answer format: set "answer" to that node label as a string.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the last node in the unique topological order.
Example JSON:
{"annotation":[180,160],"answer":"A"}
```

### task_graph__node_link__topological_endpoint_node_label / last_in_topological_order_label / answer_only / sample 345994588924632

- `instance_seed`: `345994588924632`
- `word_count`: `36`
- `body_word_count`: `18`

```text
This diagram shows a labeled directed acyclic graph. Using the graph's unique topological order, which node comes last?
Format for the "answer" field: set "answer" to that node label as a string.
Example JSON:
{"answer":"A"}
```

### task_graph__node_link__unique_cycle_size / single / answer_and_annotation / sample 2190540394932312

- `instance_seed`: `2190540394932312`
- `word_count`: `69`
- `body_word_count`: `21`

```text
The visual shows a labeled undirected graph that contains exactly one cycle. How many nodes lie on the graph's unique cycle?
Final answer format: set "answer" to the number of nodes in the unique cycle as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all nodes in the unique cycle.
Example JSON:
{"annotation":[[180,220],[310,180]],"answer":2}
```

### task_graph__node_link__unique_cycle_size / single / answer_only / sample 2190540394932312

- `instance_seed`: `2190540394932312`
- `word_count`: `42`
- `body_word_count`: `21`

```text
The visual shows a labeled undirected graph that contains exactly one cycle. How many nodes lie on the graph's unique cycle?
Required answer format: set "answer" to the number of nodes in the unique cycle as an integer.
Example JSON:
{"answer":2}
```

### task_graph__node_link__unique_related_node_label / unique_neighbor_label / answer_and_annotation / sample 4579128843647250

- `instance_seed`: `4579128843647250`
- `word_count`: `58`
- `body_word_count`: `16`

```text
The visual shows a labeled undirected graph. Which node is the only neighbor of node X?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the only node adjacent to X.
Example JSON:
{"annotation":[303,187],"answer":"B"}
```

### task_graph__node_link__unique_related_node_label / unique_neighbor_label / answer_only / sample 4579128843647250

- `instance_seed`: `4579128843647250`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The visual shows a labeled undirected graph. Which node is the only neighbor of node X?
Answer field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"B"}
```

### task_graph__node_link__unique_related_node_label / unique_predecessor_label / answer_and_annotation / sample 494229778049176

- `instance_seed`: `494229778049176`
- `word_count`: `63`
- `body_word_count`: `17`

```text
The diagram shows a labeled directed graph. Which node is the only direct predecessor of node K?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the only node with an arrow pointing into K.
Required answer format: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"annotation":[303,187],"answer":"B"}
```

### task_graph__node_link__unique_related_node_label / unique_predecessor_label / answer_only / sample 494229778049176

- `instance_seed`: `494229778049176`
- `word_count`: `39`
- `body_word_count`: `17`

```text
The diagram shows a labeled directed graph. Which node is the only direct predecessor of node K?
Format for the "answer" field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"B"}
```

### task_graph__node_link__unique_related_node_label / unique_successor_label / answer_and_annotation / sample 2446227078048533

- `instance_seed`: `2446227078048533`
- `word_count`: `65`
- `body_word_count`: `19`

```text
The diagram shows a labeled directed graph. Identify the unique direct successor of node "Awa". What is its label?
Answer format: set "answer" to the answer node label as a string exactly as shown.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the only node reached by an outgoing arrow from "Awa".
Example JSON:
{"annotation":[303,187],"answer":"B"}
```

### task_graph__node_link__unique_related_node_label / unique_successor_label / answer_only / sample 2446227078048533

- `instance_seed`: `2446227078048533`
- `word_count`: `41`
- `body_word_count`: `19`

```text
The diagram shows a labeled directed graph. Identify the unique direct successor of node "Awa". What is its label?
Format for the "answer" field: set "answer" to the answer node label as a string exactly as shown.
Example JSON:
{"answer":"B"}
```

### task_graph__pedigree_chart__relatedness_coefficient_label / single / answer_and_annotation / sample 7544740635835010

- `instance_seed`: `7544740635835010`
- `word_count`: `76`
- `body_word_count`: `27`

```text
The diagram shows a labeled pedigree chart with family connections and answer options. Trace the family connections. Which option is the relatedness coefficient for III-3 and III-4?
Annotation format: set "annotation" to a JSON array of [x0,y0,x1,y1] pixel boxes around the person symbols involved in the family connection.
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[[220,210,260,250],[410,340,450,380]],"answer":"C"}
```

### task_graph__pedigree_chart__relatedness_coefficient_label / single / answer_only / sample 7544740635835010

- `instance_seed`: `7544740635835010`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The diagram shows a labeled pedigree chart with family connections and answer options. Trace the family connections. Which option is the relatedness coefficient for III-3 and III-4?
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_graph__pedigree_chart__relationship_label / single / answer_and_annotation / sample 6879659836813505

- `instance_seed`: `6879659836813505`
- `word_count`: `73`
- `body_word_count`: `24`

```text
The diagram shows a labeled pedigree chart with family connections and answer options. Read the pedigree chart. Which option is I-2 relative to III-2?
Answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON array of [x0,y0,x1,y1] pixel boxes around the person symbols involved in the family connection.
Example JSON:
{"annotation":[[220,210,260,250],[410,340,450,380]],"answer":"A"}
```

### task_graph__pedigree_chart__relationship_label / single / answer_only / sample 6879659836813505

- `instance_seed`: `6879659836813505`
- `word_count`: `41`
- `body_word_count`: `24`

```text
The diagram shows a labeled pedigree chart with family connections and answer options. Read the pedigree chart. Which option is I-2 relative to III-2?
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"A"}
```

### task_graph__phylogeny_tree__clade_leaf_count / single / answer_and_annotation / sample 1511199504800856

- `instance_seed`: `1511199504800856`
- `word_count`: `82`
- `body_word_count`: `28`

```text
You are shown a rooted phylogeny cladogram with labeled taxa and one marked clade. The highlighted branch marks one clade. How many terminal taxa does that clade contain?
Final answer format: set "answer" to the number of descendant taxa in the marked clade as an integer.
Annotation format: set "annotation" to a JSON array of [x,y] pixel points at the terminal centers of every descendant taxon in the marked clade.
Example JSON:
{"annotation":[[742,188],[742,282],[742,376]],"answer":3}
```

### task_graph__phylogeny_tree__clade_leaf_count / single / answer_only / sample 1511199504800856

- `instance_seed`: `1511199504800856`
- `word_count`: `52`
- `body_word_count`: `28`

```text
You are shown a rooted phylogeny cladogram with labeled taxa and one marked clade. The highlighted branch marks one clade. How many terminal taxa does that clade contain?
Format for the "answer" field: set "answer" to the number of descendant taxa in the marked clade as an integer.
Example JSON:
{"answer":3}
```

### task_graph__phylogeny_tree__mrca_clade_membership_count / single / answer_and_annotation / sample 2192802058999740

- `instance_seed`: `2192802058999740`
- `word_count`: `87`
- `body_word_count`: `25`

```text
The figure shows a rooted phylogeny cladogram with labeled taxa. Find the smallest clade containing "H" and "J". How many terminal taxa are in it?
Annotation format: set "annotation" to a JSON array of [x,y] pixel points at the terminal centers of every taxon descending from the most recent common ancestor.
Format for the "answer" field: set "answer" to the number of taxa descending from the most recent common ancestor as an integer.
Example JSON:
{"annotation":[[742,180],[742,240],[742,300],[742,360]],"answer":4}
```

### task_graph__phylogeny_tree__mrca_clade_membership_count / single / answer_only / sample 2192802058999740

- `instance_seed`: `2192802058999740`
- `word_count`: `51`
- `body_word_count`: `25`

```text
The figure shows a rooted phylogeny cladogram with labeled taxa. Find the smallest clade containing "H" and "J". How many terminal taxa are in it?
Format for the "answer" field: set "answer" to the number of taxa descending from the most recent common ancestor as an integer.
Example JSON:
{"answer":4}
```

### task_graph__phylogeny_tree__sister_leaf_label / single / answer_and_annotation / sample 3322732618402841

- `instance_seed`: `3322732618402841`
- `word_count`: `62`
- `body_word_count`: `22`

```text
The diagram shows a rooted phylogeny cladogram with labeled taxa. In the cladogram, which terminal taxon shares an immediate parent with "J"?
Annotation format: set "annotation" to the [x,y] pixel point at the center of the sister taxon leaf.
Answer format: set "answer" to the sister taxon label as a string exactly as shown.
Example JSON:
{"annotation":[742,248],"answer":"B"}
```

### task_graph__phylogeny_tree__sister_leaf_label / single / answer_only / sample 3322732618402841

- `instance_seed`: `3322732618402841`
- `word_count`: `42`
- `body_word_count`: `22`

```text
The diagram shows a rooted phylogeny cladogram with labeled taxa. In the cladogram, which terminal taxon shares an immediate parent with "J"?
Required answer format: set "answer" to the sister taxon label as a string exactly as shown.
Example JSON:
{"answer":"B"}
```

### task_graph__phylogeny_tree__topology_outlier_label / single / answer_and_annotation / sample 5478081830371182

- `instance_seed`: `5478081830371182`
- `word_count`: `67`
- `body_word_count`: `25`

```text
You are shown four labeled rooted phylogeny cladograms with the same taxon labels. Ignoring rotations and drawing layout, select the one cladogram whose topology differs.
Annotation format: set "annotation" to a [x0,y0,x1,y1] pixel box around the selected option panel.
Format for the "answer" field: set "answer" to the exact option letter of the topology outlier.
Example JSON:
{"annotation":[472,520,828,742],"answer":"D"}
```

### task_graph__phylogeny_tree__topology_outlier_label / single / answer_only / sample 5478081830371182

- `instance_seed`: `5478081830371182`
- `word_count`: `42`
- `body_word_count`: `25`

```text
You are shown four labeled rooted phylogeny cladograms with the same taxon labels. Ignoring rotations and drawing layout, select the one cladogram whose topology differs.
Answer format: set "answer" to the exact option letter of the topology outlier.
Example JSON:
{"answer":"D"}
```

### task_graph__pipe_network__bridge_count / single / answer_and_annotation / sample 150369676515663

- `instance_seed`: `150369676515663`
- `word_count`: `110`
- `body_word_count`: `34`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the open pipe segments whose removal would split the connected open-pipe network.
Annotation format: set "annotation" to a list of segments. Each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel point at a junction center of one open pipe whose removal disconnects part of the open network; use [] when the answer is zero.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[[180,220],[310,220]],[[310,220],[430,300]]],"answer":2}
```

### task_graph__pipe_network__bridge_count / single / answer_only / sample 150369676515663

- `instance_seed`: `150369676515663`
- `word_count`: `51`
- `body_word_count`: `34`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the open pipe segments whose removal would split the connected open-pipe network.
Answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```

### task_graph__pipe_network__pipe_exact_distance_count / single / answer_and_annotation / sample 1876734353903208

- `instance_seed`: `1876734353903208`
- `word_count`: `90`
- `body_word_count`: `35`

```text
The visual shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the junctions whose shortest open route from 16 uses exactly 3 pipe segments.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all junctions whose shortest open-pipe distance from 16 is exactly 3 segments.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,220],[430,300]],"answer":3}
```

### task_graph__pipe_network__pipe_exact_distance_count / single / answer_only / sample 1876734353903208

- `instance_seed`: `1876734353903208`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The visual shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the junctions whose shortest open route from 16 uses exactly 3 pipe segments.
Answer field: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":3}
```

### task_graph__pipe_network__pipe_reachable_junction_count / single / answer_and_annotation / sample 2831408051682714

- `instance_seed`: `2831408051682714`
- `word_count`: `86`
- `body_word_count`: `33`

```text
The figure shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the junctions reachable through open pipes from 5, including 5 itself.
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of all junctions reachable from 5 through open pipes, including 5 itself.
Required answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,220],[430,300]],"answer":3}
```

### task_graph__pipe_network__pipe_reachable_junction_count / single / answer_only / sample 2831408051682714

- `instance_seed`: `2831408051682714`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The figure shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Count the junctions reachable through open pipes from 5, including 5 itself.
Answer format: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":3}
```

### task_graph__pipe_network__shortest_path_length / single / answer_and_annotation / sample 5971122719632057

- `instance_seed`: `5971122719632057`
- `word_count`: `98`
- `body_word_count`: `42`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Ignoring blocked pipes, what is the length in pipe segments of the shortest open route from junction V to junction B?
Annotation format: set "annotation" to an ordered array of [x,y] pixel points at junction centers along the unique shortest open route from V to B, including both endpoints.
Format for the "answer" field: set "answer" to the requested count or length as an integer.
Example JSON:
{"annotation":[[180,220],[310,220],[430,300]],"answer":2}
```

### task_graph__pipe_network__shortest_path_length / single / answer_only / sample 5971122719632057

- `instance_seed`: `5971122719632057`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The diagram shows a labeled pipe-junction network with open pipes and blocked pipes (blocked pipes are marked with a red X). Ignoring blocked pipes, what is the length in pipe segments of the shortest open route from junction V to junction B?
Answer field: set "answer" to the requested count or length as an integer.
Example JSON:
{"answer":2}
```
