# `task_games__checkers__piece_mobility_count`

## Contract
1. Domain: `games`
2. Task group: `checkers`
3. Scene id: `checkers`
4. Public task id: `task_games__checkers__piece_mobility_count`
5. Supported `query_id` values: `piece_with_capture_move_count`, `piece_with_legal_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(unique(origins(filter(legal_moves(current_player), move_filter)))); scene=checkers; scope=piece_mobility_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the centers of current-player source pieces that have at least one qualifying move.
