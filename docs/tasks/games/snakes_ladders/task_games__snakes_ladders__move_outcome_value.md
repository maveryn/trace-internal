# `task_games__snakes_ladders__move_outcome_value`

## Contract
1. Domain: `games`
2. Scene id: `snakes_ladders`
3. Public task id: `task_games__snakes_ladders__move_outcome_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_map`
7. Program schema: `value(simulate(start_square, rules=snakes_ladders_jumps, action=shown_die).final_square); scene=snakes_ladders; scope=move_outcome_value`
8. Scalar annotation checked: `true`

## Program Contract
- `value(simulate(start_square, rules=snakes_ladders_jumps, action=shown_die).final_square); scene=snakes_ladders; scope=move_outcome_value`

## Generation Notes
1. Move the token by the shown die value, then immediately follow a snake or ladder if the landing square starts one.
2. Annotation is a bbox map with `start_square` and `end_square` roles.
3. Prompt wording comes from `prompts/games/snakes_ladders/games_snakes_ladders_v1.json`.
