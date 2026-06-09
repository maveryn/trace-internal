# `task_games__chess__target_square_attacker_count`

1. Domain: `games`
2. Task group: `chess`
3. Scene ID: `chess`
4. Public task id: `task_games__chess__target_square_attacker_count`
5. Supported `query_id` values: `king_square_attacker_count`, `white_piece_attacks_target_square_count`, `black_piece_attacks_target_square_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(attackers(marked_target_square, queried_side)); scene=chess; scope=target_square_attacker_count`
9. Annotation contract: mark bounding boxes for all attacking pieces from the queried side. For `king_square_attacker_count`, the marked target square contains the king and the queried side is the opponent. For the white/black target-square queries, the marked target square is empty.
