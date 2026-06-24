# `task_games__ultimate_tictactoe__small_board_status_count`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__small_board_status_count`
5. Supported `query_id` values: `x_won_board_count`, `o_won_board_count`, `neither_won_board_count`, `drawn_board_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(filter(local_boards, board_status=target_status)); scene=ultimate_tictactoe; scope=small_board_status_count`

## Generation Notes
1. Query ids choose which small-board status category is counted.
2. Annotation contains one small-board bbox for each counted board.
3. Query ids are internal replay keys and do not define public task units.
4. `scalar_annotation_checked=true`
