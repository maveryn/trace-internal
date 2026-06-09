# `task_games__tower_defense__covered_path_segment_count`

## Contract
1. Domain: `games`
2. Task group: `tower_defense`
3. Scene id: `tower_defense`
4. Public task id: `task_games__tower_defense__covered_path_segment_count`
5. Supported `query_id` values: `covered_path_segment_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(path_node for path_node in path_nodes if any(path_node_center inside tower_range_circle for tower in towers)); scene=tower_defense; scope=covered_path_segment_count`

## Generation Notes
1. The path is drawn as discrete visible nodes along a winding or switchback route.
2. Towers are placed off the path and display circular range rings.
3. A path node is covered when its center lies inside at least one tower range ring.
4. Annotation contains one point at the center of every covered path node.
