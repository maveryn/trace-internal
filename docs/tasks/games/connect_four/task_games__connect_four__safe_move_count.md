# `task_games__connect_four__safe_move_count`

## Contract
1. Domain: `games`
2. Scene id: `connect_four`
3. Public task id: `task_games__connect_four__safe_move_count`
4. Supported `query_id` values: `safe_move_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(legal_columns, opponent_wins_next=False)); scene=connect_four; scope=safe_move_count`

## Program Contract
- `count(filter(legal_columns, opponent_wins_next=False)); scene=connect_four; scope=safe_move_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
