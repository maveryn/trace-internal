# `task_games__tower_defense__nearest_exit_enemy_label`

## Contract
1. Domain: `games`
2. Scene: `tower_defense`
3. Scene id: `tower_defense`
4. Public task id: `task_games__tower_defense__nearest_exit_enemy_label`
5. Supported `query_id` values: `single`
6. Answer schema: `label`
7. Annotation schema: `point`

## Program Contract

`argmax_label(enemy in labeled_enemies_A_to_F, path_index(enemy)); scene=tower_defense; scope=nearest_exit_enemy_label`

## Generation Notes
1. The path has six labeled enemy markers `A` through `F`.
2. The exit is marked near the final path endpoint.
3. Closeness to the exit is path order, not straight-line distance.
4. The answer is the label of the enemy farthest along the path toward the exit.
5. Annotation is the point at the center of the selected labeled enemy.
