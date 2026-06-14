# `task_games__reversi__legal_destination_count`

## Contract
1. Domain: `games`
2. Scene: `reversi`
3. Scene id: `reversi`
4. Public task id: `task_games__reversi__legal_destination_count`
5. Supported `query_id` values: `corner_move_count`, `legal_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(legal_moves(current_player), destination_filter)); scene=reversi; scope=legal_destination_count; query_branch=corner_move_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
