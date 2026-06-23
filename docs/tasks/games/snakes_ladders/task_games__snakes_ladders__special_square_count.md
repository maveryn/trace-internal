# `task_games__snakes_ladders__special_square_count`

## Contract
1. Domain: `games`
2. Scene id: `snakes_ladders`
3. Public task id: `task_games__snakes_ladders__special_square_count`
4. Supported `query_id` values: `ladder_start_ahead_count`, `snake_head_ahead_count`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(jump_starts(kind=query_kind, square > token_square, square <= final_square)); scene=snakes_ladders; scope=special_square_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(jump_starts(kind=query_kind, square > token_square, square <= final_square)); scene=snakes_ladders; scope=special_square_count`

## Generation Notes
1. Count by square number from just after the token through the final square; do not move the token or follow jumps.
2. Annotation is the bbox set for all counted ladder-start or snake-head squares, and is empty when the answer is 0.
3. Prompt wording comes from `prompts/games/snakes_ladders/games_snakes_ladders_v1.json`.
