# `task_games__connect_four__winning_move_count`

## Contract
1. Domain: `games`
2. Task group: `connect_four`
3. Scene id: `connect_four`
4. Public task id: `task_games__connect_four__winning_move_count`
5. Supported `query_id` values: `winning_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(legal_columns, move_result=win_for_current_player)); scene=connect_four; scope=winning_move_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
