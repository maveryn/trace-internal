# `task_games__snake__snake_length_count`

## Contract
1. Domain: `games`
2. Scene id: `snake`
3. Public task id: `task_games__snake__snake_length_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(snake_occupied_cells); scene=snake; scope=snake_length_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(snake_occupied_cells); scene=snake; scope=snake_length_count`

## Generation Notes
1. Count all snake-occupied cells, including the head and every body/tail cell.
2. Annotation is the bbox set for the same occupied cells counted in the answer.
3. Prompt wording comes from `prompts/games/snake/games_snake_v1.json`.
