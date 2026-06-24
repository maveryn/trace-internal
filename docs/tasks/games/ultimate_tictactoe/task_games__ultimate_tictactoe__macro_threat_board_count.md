# `task_games__ultimate_tictactoe__macro_threat_board_count`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__macro_threat_board_count`
5. Supported `query_id` values: `x_immediate_win_board_count`, `o_immediate_win_board_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(filter(local_boards, status=open and immediate_win_exists(player))); scene=ultimate_tictactoe; scope=macro_threat_board_count`

## Generation Notes
1. Query ids choose whether X or O immediate-win boards are counted.
2. Annotation contains the small-board bboxes for every counted board.
3. Empty annotation is valid when the answer is `0`.
4. `scalar_annotation_checked=true`
