# `task_games__snakes_ladders__best_roll_value`

## Contract
1. Domain: `games`
2. Scene id: `snakes_ladders`
3. Public task id: `task_games__snakes_ladders__best_roll_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox`
7. Program schema: `argmax_value(roll_plans, transition_rule=snakes_ladders_jumps, objective=final_square_after_roll_plan(start_square, horizon_roll_count)); scene=snakes_ladders; scope=best_roll_value`
8. Scalar annotation checked: `true`

## Program Contract
- `argmax_value(roll_plans, transition_rule=snakes_ladders_jumps, objective=final_square_after_roll_plan(start_square, horizon_roll_count)); scene=snakes_ladders; scope=best_roll_value`

## Generation Notes
1. Choose each roll value from 1 through 6 for the stated horizon and return the highest reachable final square.
2. Annotation is the bbox of the final square named in the answer.
3. Prompt wording comes from `prompts/games/snakes_ladders/games_snakes_ladders_v1.json`.
