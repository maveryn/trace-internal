# Graph Calibration

Historical note: the numeric task stats in this table are from the earlier `Qwen/Qwen3-VL-2B-Instruct` 32-rollout probe and should be treated as reference only. Active calibration work should use fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` probes.
Tasks in this domain: 10

| Task | Direction | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Low omission frac | High omission frac | Task record |
|---|---|---:|---:|---:|---:|---:|---|
| task_graph_comparison_largest_component_size | review | 0.2818 | 0.0258 | 0.0000 | 0.1961 | 0.0172 | [task_graph_comparison_largest_component_size](task_graph_comparison_largest_component_size.md) |
| task_graph_counting_articulation_point_count | make_easier | 0.0759 | 0.4062 | 0.0000 | 0.7836 | 0.0000 | [task_graph_counting_articulation_point_count](task_graph_counting_articulation_point_count.md) |
| task_graph_counting_bridge_count | make_easier | 0.1009 | 0.3031 | 0.0000 | 0.6453 | 0.0000 | [task_graph_counting_bridge_count](task_graph_counting_bridge_count.md) |
| task_graph_counting_degree_count | make_easier | 0.1931 | 0.2477 | 0.0078 | 0.5547 | 0.0578 | [task_graph_counting_degree_count](task_graph_counting_degree_count.md) |
| task_graph_optimization_minimum_spanning_tree_weight | make_easier | 0.0134 | 0.7320 | 0.0000 | 0.9805 | 0.0000 | [task_graph_optimization_minimum_spanning_tree_weight](task_graph_optimization_minimum_spanning_tree_weight.md) |
| task_graph_order_topological_position | make_easier | 0.0917 | 0.2711 | 0.0000 | 0.7031 | 0.0000 | [task_graph_order_topological_position](task_graph_order_topological_position.md) |
| task_graph_path_shortest_path_length | review | 0.3750 | 0.0563 | 0.0008 | 0.1789 | 0.0680 | [task_graph_path_shortest_path_length](task_graph_path_shortest_path_length.md) |
| task_graph_relation_reachable_count | make_easier | 0.1366 | 0.2023 | 0.0000 | 0.5555 | 0.0023 | [task_graph_relation_reachable_count](task_graph_relation_reachable_count.md) |
| task_graph_relation_same_component_count | make_easier | 0.2226 | 0.1406 | 0.0000 | 0.3773 | 0.0172 | [task_graph_relation_same_component_count](task_graph_relation_same_component_count.md) |
| task_graph_relation_unique_cycle_size | make_easier | 0.1960 | 0.1648 | 0.0000 | 0.6039 | 0.0531 | [task_graph_relation_unique_cycle_size](task_graph_relation_unique_cycle_size.md) |
