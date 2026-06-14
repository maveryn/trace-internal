# `task_games__snakes_ladders__special_square_count`

## Contract
1. Domain: `games`
2. Scene: `snakes_ladders`
3. Scene id: `snakes_ladders`
4. Public task id: `task_games__snakes_ladders__special_square_count`
5. Supported `query_id` values: `ladder_start_ahead_count`, `snake_head_ahead_count`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `count(jump_starts(kind=query_kind, square > token_square, square <= final_square)); scene=snakes_ladders; scope=special_square_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
