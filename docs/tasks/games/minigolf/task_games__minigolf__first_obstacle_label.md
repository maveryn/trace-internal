# `task_games__minigolf__first_obstacle_label`

## Contract
1. Domain: `games`
2. Scene id: `minigolf`
3. Public task id: `task_games__minigolf__first_obstacle_label`
4. Supported `query_id` values: `first_obstacle_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_set`
7. Program schema: `label(first_collision(shot_path, obstacles)); scene=minigolf; scope=first_obstacle_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
