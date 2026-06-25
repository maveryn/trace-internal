# `task_games__tower_defense__best_tower_position_label`

## Contract
1. Domain: `games`
2. Scene: `tower_defense`
3. Scene id: `tower_defense`
4. Public task id: `task_games__tower_defense__best_tower_position_label`
5. Supported `query_id` values: `single`
6. Answer schema: `label`
7. Annotation schema: `point`

## Program Contract

`argmax_label(candidate in candidates_A_to_D, count(path_enemy for path_enemy in path_enemies if path_enemy_center inside candidate_range_circle)); scene=tower_defense; scope=best_tower_position_label`

## Generation Notes
1. The path is drawn with small visible enemy markers along a winding or switchback route.
2. Four candidate tower positions are labeled `A`, `B`, `C`, and `D`, each with a circular range ring.
3. All four candidate tower range rings use the same radius within an instance.
4. A candidate covers a path enemy when the enemy center lies inside that candidate's range ring.
5. Exactly one candidate covers the most path enemies by construction.
6. Annotation is the point at the center of the selected candidate tower.
