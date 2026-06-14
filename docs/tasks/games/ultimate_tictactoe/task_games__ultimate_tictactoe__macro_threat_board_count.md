# `task_games__ultimate_tictactoe__macro_threat_board_count`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__macro_threat_board_count`
5. Supported `query_id` values: `x_immediate_win_board_count`, `o_immediate_win_board_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(local_boards, status=open and immediate_win_exists(player))); scene=ultimate_tictactoe; scope=macro_threat_board_count`

## Generation Notes
2. Query ids choose the player whose one-move local wins are counted.
3. Annotation contains the small-board bounding boxes for every counted board; empty annotation is valid when the answer is `0`.
