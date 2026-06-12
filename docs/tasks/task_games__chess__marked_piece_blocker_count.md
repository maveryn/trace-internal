# `task_games__chess__marked_piece_blocker_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Public task id: `task_games__chess__marked_piece_blocker_count`
4. Supported `query_id` values: `rook_line_blocker_count`, `bishop_diagonal_blocker_count`, `queen_line_blocker_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(pieces strictly between marked_slider and target_square); scene=chess; scope=marked_piece_blocker_count`

## Generation Notes
1. The red outlined square contains the source sliding piece.
2. The blue outlined square marks an empty target square aligned with the source piece.
3. Annotation marks only pieces strictly between the source and target squares.
