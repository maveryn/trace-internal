# `task_games__ultimate_tictactoe__small_board_status_count`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__small_board_status_count`
5. Supported `query_id` values: `drawn_board_count`, `neither_won_board_count`, `o_won_board_count`, `x_won_board_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(local_boards, board_status=target_status)); scene=ultimate_tictactoe; scope=small_board_status_count; query_branch=drawn_board_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
