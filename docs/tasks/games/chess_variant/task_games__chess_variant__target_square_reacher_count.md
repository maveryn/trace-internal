# `task_games__chess_variant__target_square_reacher_count`

## Contract
1. Domain: `games`
2. Scene id: `chess_variant`
3. Public task id: `task_games__chess_variant__target_square_reacher_count`
4. Supported `query_id` values: `white_piece_reaches_target_count`, `black_piece_reaches_target_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(pieces(target_color), target_square in legal_destinations(piece))); scene=chess_variant; scope=target_square_reacher_count`

## Program Contract
- `count(filter(pieces(target_color), target_square in legal_destinations(piece))); scene=chess_variant; scope=target_square_reacher_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. The blue outlined square is the target square; annotation marks the source-piece boxes that can legally reach it.
