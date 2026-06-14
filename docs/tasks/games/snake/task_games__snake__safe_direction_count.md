# `task_games__snake__safe_direction_count`

## Contract
1. Domain: `games`
2. Scene: `snake`
3. Scene id: `snake`
4. Public task id: `task_games__snake__safe_direction_count`
5. Supported `query_id` values: `safe_direction_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(directions, move_collision(direction)=False)); scene=snake; scope=safe_direction_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
