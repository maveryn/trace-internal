# `task_games__circular_chess__target_cell_reacher_count`

## Contract
1. Domain: `games`
2. Scene id: `circular_chess`
3. Public task id: `task_games__circular_chess__target_cell_reacher_count`
4. Supported `query_id` values: `black_piece_reaches_target_count`, `white_piece_reaches_target_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(pieces(target_color), target_cell in legal_destinations(piece))); scene=circular_chess; scope=target_cell_reacher_count`

## Program Contract
- `count(filter(pieces(target_color), target_cell in legal_destinations(piece))); scene=circular_chess; scope=target_cell_reacher_count`

## Generation Notes
1. The blue marker identifies the target cell.
2. Pawns, check, checkmate, castling, en passant, and promotion are intentionally out of scope.
3. Annotation marks source-piece centers as pixel-space points.
