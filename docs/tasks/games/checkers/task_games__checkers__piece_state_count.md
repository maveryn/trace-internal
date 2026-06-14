# `task_games__checkers__piece_state_count`

## Contract
1. Domain: `games`
2. Scene package: `checkers`
3. Scene id: `checkers`
4. Public task id: `task_games__checkers__piece_state_count`
5. Supported `query_id` values: `black_edge_piece_count`, `black_piece_count`, `red_edge_piece_count`, `red_piece_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(checkers_pieces(board_state), piece_color, board_edge_state)); scene=checkers; scope=piece_state_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the centers of visible pieces that satisfy the color and board-edge condition.
