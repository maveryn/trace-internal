# Annotation Projection Validation

- sampled instances: `95`
- query ids covered: `95`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 5, 'bbox_sequence': 2, 'bbox_set': 6, 'point': 12, 'point_map': 6, 'point_sequence': 15, 'point_set': 36, 'segment_set': 13}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
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

## Issues

No issues found.
