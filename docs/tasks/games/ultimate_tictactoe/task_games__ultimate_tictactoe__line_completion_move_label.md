# `task_games__ultimate_tictactoe__line_completion_move_label`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__line_completion_move_label`
5. Supported `query_id` values: `o_blocking_move_label`, `o_winning_move_label`, `x_blocking_move_label`, `x_winning_move_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(filter(local_board_cells, local_line_completion_rule(player, cell, tactic_kind)=True)); scene=ultimate_tictactoe; scope=line_completion_move_label; query_branch=o_blocking_move_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
