# `task_games__chess__king_escape_square_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Public task id: `task_games__chess__king_escape_square_count`
4. Supported `query_id` values: `king_escape_square_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(legal_escape_squares(king)); scene=chess; scope=king_escape_square_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
