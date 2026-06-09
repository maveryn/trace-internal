# `task_games__snakes_ladders__best_roll_value`

## Contract
1. Domain: `games`
2. Task group: `snakes_ladders`
3. Scene id: `snakes_ladders`
4. Public task id: `task_games__snakes_ladders__best_roll_value`
5. Supported `query_id` values: `best_roll_value`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `argmax_value(roll_plans, transition_rule=jumps, objective=final_square_after_roll_plan(start_square, jumps, horizon_roll_count)); scene=snakes_ladders; scope=best_roll_value`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
