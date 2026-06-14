# `task_games__snakes_ladders__move_outcome_value`

## Contract
1. Domain: `games`
2. Scene: `snakes_ladders`
3. Scene id: `snakes_ladders`
4. Public task id: `task_games__snakes_ladders__move_outcome_value`
5. Supported `query_id` values: `move_outcome_value`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`
8. Program schema: `value(simulate(start_square, rules=jumps, action=die_value).final_square); scene=snakes_ladders; scope=move_outcome_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
