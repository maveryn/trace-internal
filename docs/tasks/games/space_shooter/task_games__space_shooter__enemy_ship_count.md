# `task_games__space_shooter__enemy_ship_count`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__enemy_ship_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(enemy_ships); scene=space_shooter; scope=enemy_ship_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the bbox set of every visible enemy ship; the player ship and all projectiles are distractors.
3. Red enemy-shot distractor lanes may contain one to three visible shots.
4. Blue player shots are placed below all same-lane enemy ships and red enemy shots.
5. Scalar annotation checked: true.
