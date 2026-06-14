# `task_games__hex__connection_gap_count`

## Contract
1. Domain: `games`
2. Scene: `hex`
3. Scene id: `hex`
4. Public task id: `task_games__hex__connection_gap_count`
5. Supported `query_id` values: `connection_gap_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(connection_gap_cells(player, board_state)); scene=hex; scope=connection_gap_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
