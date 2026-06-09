# `task_games__hex__winning_move_cell_label`

## Contract
1. Domain: `games`
2. Task group: `hex`
3. Scene id: `hex`
4. Public task id: `task_games__hex__winning_move_cell_label`
5. Supported `query_id` values: `winning_move_cell_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(filter(empty_cells, move_result=connects_player_sides)); scene=hex; scope=winning_move_cell_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
