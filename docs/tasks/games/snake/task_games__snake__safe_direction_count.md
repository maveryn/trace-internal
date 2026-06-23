# `task_games__snake__safe_direction_count`

## Program Contract
1. Domain: `games`
2. Scene: `snake`
3. Public task id: `task_games__snake__safe_direction_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(cardinal_directions, snake_next_cell_is_safe)); scene=snake; scope=safe_direction_count`
8. Scalar annotation checked: `true`

## Generation Notes
1. Count the immediate up/down/left/right moves that keep the head inside the board and out of the body or gray walls.
2. Annotation is the bbox set for safe destination cells. It is empty when no direction is safe.
3. Prompt wording comes from `prompts/games/snake/games_snake_v1.json`.
