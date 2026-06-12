# `task_games__chess__target_square_attacker_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Public task id: `task_games__chess__target_square_attacker_count`
4. Supported `query_id` values: `king_square_attacker_count`, `white_piece_attacks_target_square_count`, `black_piece_attacks_target_square_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(attackers(marked_target_square, queried_side)); scene=chess; scope=target_square_attacker_count`

## Generation Notes
1. Annotation marks bounding boxes for all attacking pieces from the queried side.
2. For `king_square_attacker_count`, the marked target square contains the king and the queried side is the opponent.
3. For the white/black target-square queries, the marked target square is empty.
