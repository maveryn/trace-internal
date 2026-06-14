# `task_games__checkers__move_count`

## Contract
1. Domain: `games`
2. Scene package: `checkers`
3. Scene id: `checkers`
4. Public task id: `task_games__checkers__move_count`
5. Supported `query_id` values: `capture_move_count`, `legal_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(legal_moves(current_player), move_filter)); scene=checkers; scope=move_count; query_branch=capture_move_count`

## Program Contract
- `count(filter(legal_moves(current_player), move_filter)); scene=checkers; scope=move_count; query_branch=capture_move_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
