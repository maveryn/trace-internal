# `task_games__reversi__marked_move_flip_count`

## Contract
1. Domain: `games`
2. Scene: `reversi`
3. Scene id: `reversi`
4. Public task id: `task_games__reversi__marked_move_flip_count`
5. Supported `query_id` values: `flip_count_for_marked_move`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(flipped_discs(transform(board, marked_move))); scene=reversi; scope=marked_move_flip_count; query_branch=flip_count_for_marked_move`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
