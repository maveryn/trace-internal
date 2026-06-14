# `task_games__tower_defense__tower_coverage_count`

## Contract
1. Domain: `games`
2. Scene: `tower_defense`
3. Scene id: `tower_defense`
4. Public task id: `task_games__tower_defense__tower_coverage_count`
5. Supported `query_id` values: `marked_enemy_covered_by_tower_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(tower for tower in towers if marked_enemy_center inside tower_range_circle); scene=tower_defense; scope=tower_coverage_count`

## Generation Notes
1. The marked enemy lies on a visible discrete path point.
2. Towers are placed off the path and display circular range rings.
3. Annotation contains one point at the center of every tower whose range ring covers the marked enemy.
4. Empty annotation is valid when no tower covers the marked enemy.
