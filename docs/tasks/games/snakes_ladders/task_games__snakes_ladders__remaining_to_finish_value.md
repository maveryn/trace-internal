# `task_games__snakes_ladders__remaining_to_finish_value`

## Contract
1. Domain: `games`
2. Scene id: `snakes_ladders`
3. Public task id: `task_games__snakes_ladders__remaining_to_finish_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_map`
7. Program schema: `value(final_square - token_square); scene=snakes_ladders; scope=remaining_to_finish_value`
8. Scalar annotation checked: `true`

## Program Contract
- `value(final_square - token_square); scene=snakes_ladders; scope=remaining_to_finish_value`

## Generation Notes
1. Use the numbered board only; do not roll dice or follow snakes/ladders.
2. Annotation is a bbox map with `token_square` and `finish_square` roles.
3. Prompt wording comes from `prompts/games/snakes_ladders/games_snakes_ladders_v1.json`.
