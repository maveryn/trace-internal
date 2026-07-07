# Duplicate Candidate Scan: graph

No exact same-scene program/answer/annotation duplicate candidates were found by the static scan.

## Closest Same-Scene Neighbors

| Scene | Task | Closest neighbor | Decision |
| --- | --- | --- | --- |
| `adjacency` | `task_graph__adjacency__directed_pair_reciprocity_count` | `task_graph__adjacency__directed_strong_component_count (0.31)` | `keep` |
| `adjacency` | `task_graph__adjacency__directed_strong_component_count` | `task_graph__adjacency__undirected_component_count (0.81)` | `keep` |
| `adjacency` | `task_graph__adjacency__mst_weight` | `task_graph__adjacency__undirected_component_count (0.37)` | `keep` |
| `adjacency` | `task_graph__adjacency__traversal_kth_label` | `task_graph__adjacency__undirected_component_count (0.27)` | `keep` |
| `adjacency` | `task_graph__adjacency__undirected_component_count` | `task_graph__adjacency__directed_strong_component_count (0.81)` | `keep` |
| `automaton` | `task_graph__automaton__dfa_accepted_string_label` | `task_graph__automaton__nfa_accepted_string_label (0.92)` | `keep` |
| `automaton` | `task_graph__automaton__nfa_accepted_string_label` | `task_graph__automaton__dfa_accepted_string_label (0.92)` | `keep` |
| `automaton` | `task_graph__automaton__nondeterministic_state_count` | `task_graph__automaton__state_after_input_label (0.30)` | `keep` |
| `automaton` | `task_graph__automaton__state_after_input_label` | `task_graph__automaton__dfa_accepted_string_label (0.47)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__bst_path_operation_label` | `task_graph__binary_tree__traversal_kth_label (0.45)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__child_structure_node_count` | `task_graph__binary_tree__depth_level_node_count (0.76)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__depth_level_node_count` | `task_graph__binary_tree__child_structure_node_count (0.76)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__heap_property_violation_label` | `task_graph__binary_tree__local_relative_node_label (0.56)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__local_relative_node_label` | `task_graph__binary_tree__heap_property_violation_label (0.56)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__lowest_common_ancestor_label` | `task_graph__binary_tree__heap_property_violation_label (0.53)` | `keep` |
| `binary_tree` | `task_graph__binary_tree__traversal_kth_label` | `task_graph__binary_tree__heap_property_violation_label (0.47)` | `keep` |
| `flow_network` | `task_graph__flow_network__max_flow_value` | `task_graph__flow_network__min_cut_edge_count (0.81)` | `keep` |
| `flow_network` | `task_graph__flow_network__min_cut_edge_count` | `task_graph__flow_network__max_flow_value (0.81)` | `keep` |
| `graph_options` | `task_graph__graph_options__contained_subgraph_label` | `task_graph__graph_options__same_structure_label (0.64)` | `keep` |
| `graph_options` | `task_graph__graph_options__same_structure_label` | `task_graph__graph_options__contained_subgraph_label (0.64)` | `keep` |
| `metro` | `task_graph__metro__exact_distance_station_count` | `task_graph__metro__station_membership_count (0.64)` | `keep` |
| `metro` | `task_graph__metro__route_condition_station_count` | `task_graph__metro__station_membership_count (0.83)` | `keep` |
| `metro` | `task_graph__metro__shortest_path_length` | `task_graph__metro__exact_distance_station_count (0.40)` | `keep` |
| `metro` | `task_graph__metro__station_membership_count` | `task_graph__metro__route_condition_station_count (0.83)` | `keep` |
| `node_link` | `task_graph__node_link__articulation_point_count` | `task_graph__node_link__bridge_count (0.56)` | `keep` |
| `node_link` | `task_graph__node_link__bridge_count` | `task_graph__node_link__edge_color_count (0.64)` | `keep` |
| `node_link` | `task_graph__node_link__common_related_node_count` | `task_graph__node_link__unique_related_node_label (0.53)` | `keep` |
| `node_link` | `task_graph__node_link__component_size_after_edge_edit` | `task_graph__node_link__same_component_count (0.62)` | `keep` |
| `node_link` | `task_graph__node_link__cross_color_edge_count` | `task_graph__node_link__edge_color_count (0.75)` | `keep` |
| `node_link` | `task_graph__node_link__degree_after_removal_filter_count` | `task_graph__node_link__isolated_after_removal_count (0.68)` | `keep` |
| `node_link` | `task_graph__node_link__degree_extremum_value` | `task_graph__node_link__degree_value_filter_count (0.53)` | `keep` |
| `node_link` | `task_graph__node_link__degree_value_filter_count` | `task_graph__node_link__named_node_degree_value (0.71)` | `keep` |
| `node_link` | `task_graph__node_link__edge_between_nodes_label` | `task_graph__node_link__edge_text_count (0.62)` | `keep` |
| `node_link` | `task_graph__node_link__edge_color_count` | `task_graph__node_link__node_color_count (0.77)` | `keep` |
| `node_link` | `task_graph__node_link__edge_text_count` | `task_graph__node_link__edge_color_count (0.67)` | `keep` |
| `node_link` | `task_graph__node_link__hamiltonian_cycle_neighbor_label` | `task_graph__node_link__unique_related_node_label (0.43)` | `keep` |
| `node_link` | `task_graph__node_link__isolated_after_removal_count` | `task_graph__node_link__degree_after_removal_filter_count (0.68)` | `keep` |
| `node_link` | `task_graph__node_link__largest_chordless_cycle_size` | `task_graph__node_link__largest_component_size (0.53)` | `keep` |
| `node_link` | `task_graph__node_link__largest_component_size` | `task_graph__node_link__same_component_count (0.53)` | `keep` |
| `node_link` | `task_graph__node_link__longest_path_length` | `task_graph__node_link__shortest_path_length (0.57)` | `keep` |
| `node_link` | `task_graph__node_link__mst_weight` | `task_graph__node_link__bridge_count (0.33)` | `keep` |
| `node_link` | `task_graph__node_link__named_node_degree_value` | `task_graph__node_link__degree_value_filter_count (0.71)` | `keep` |
| `node_link` | `task_graph__node_link__node_color_count` | `task_graph__node_link__edge_color_count (0.77)` | `keep` |
| `node_link` | `task_graph__node_link__reachable_count` | `task_graph__node_link__reachable_count_after_edge_edit (0.76)` | `keep` |
| `node_link` | `task_graph__node_link__reachable_count_after_edge_edit` | `task_graph__node_link__reachable_count (0.76)` | `keep` |
| `node_link` | `task_graph__node_link__same_component_count` | `task_graph__node_link__component_size_after_edge_edit (0.62)` | `keep` |
| `node_link` | `task_graph__node_link__shortest_path_length` | `task_graph__node_link__longest_path_length (0.57)` | `keep` |
| `node_link` | `task_graph__node_link__topological_endpoint_node_label` | `task_graph__node_link__unique_related_node_label (0.37)` | `keep` |
| `node_link` | `task_graph__node_link__unique_cycle_size` | `task_graph__node_link__node_color_count (0.57)` | `keep` |
| `node_link` | `task_graph__node_link__unique_related_node_label` | `task_graph__node_link__same_component_count (0.53)` | `keep` |
| `pedigree_chart` | `task_graph__pedigree_chart__relatedness_coefficient_label` | `task_graph__pedigree_chart__relationship_label (0.81)` | `keep` |
| `pedigree_chart` | `task_graph__pedigree_chart__relationship_label` | `task_graph__pedigree_chart__relatedness_coefficient_label (0.81)` | `keep` |
| `phylogeny_tree` | `task_graph__phylogeny_tree__clade_leaf_count` | `task_graph__phylogeny_tree__mrca_clade_membership_count (0.76)` | `keep` |
| `phylogeny_tree` | `task_graph__phylogeny_tree__mrca_clade_membership_count` | `task_graph__phylogeny_tree__clade_leaf_count (0.76)` | `keep` |
| `phylogeny_tree` | `task_graph__phylogeny_tree__sister_leaf_label` | `task_graph__phylogeny_tree__topology_outlier_label (0.41)` | `keep` |
| `phylogeny_tree` | `task_graph__phylogeny_tree__topology_outlier_label` | `task_graph__phylogeny_tree__sister_leaf_label (0.41)` | `keep` |
| `pipe_network` | `task_graph__pipe_network__bridge_count` | `task_graph__pipe_network__pipe_exact_distance_count (0.45)` | `keep` |
| `pipe_network` | `task_graph__pipe_network__pipe_exact_distance_count` | `task_graph__pipe_network__pipe_reachable_junction_count (0.64)` | `keep` |
| `pipe_network` | `task_graph__pipe_network__pipe_reachable_junction_count` | `task_graph__pipe_network__pipe_exact_distance_count (0.64)` | `keep` |
| `pipe_network` | `task_graph__pipe_network__shortest_path_length` | `task_graph__pipe_network__pipe_reachable_junction_count (0.50)` | `keep` |
