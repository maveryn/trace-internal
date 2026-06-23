# `task_games__snake__shortest_food_path_length`

## Program Contract
1. Domain: `games`
2. Scene: `snake`
3. Public task id: `task_games__snake__shortest_food_path_length`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `path.shortest_path_value(head, food, blockers=current_body_or_wall_cells); scene=snake; scope=shortest_food_path_length`
8. Scalar annotation checked: `true`

## Generation Notes
1. Find the shortest cardinal path from the head to the red food while treating current body cells and gray wall cells as fixed blockers.
2. Annotation is the bbox set for one shortest path, excluding the starting head cell and including the food cell.
3. Prompt wording comes from `prompts/games/snake/games_snake_v1.json`.
