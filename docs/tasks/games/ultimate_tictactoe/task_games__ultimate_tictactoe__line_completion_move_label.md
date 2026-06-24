# `task_games__ultimate_tictactoe__line_completion_move_label`

## Contract
1. Domain: `games`
2. Scene: `ultimate_tictactoe`
3. Scene id: `ultimate_tictactoe`
4. Public task id: `task_games__ultimate_tictactoe__line_completion_move_label`
5. Supported `query_id` values: `x_winning_move_label`, `o_winning_move_label`, `x_blocking_move_label`, `o_blocking_move_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox`

## Program Contract
`label(filter(highlighted_board_empty_cells, line_completion_move(player, tactic_kind))); scene=ultimate_tictactoe; scope=line_completion_move_label`

## Generation Notes
1. Query ids choose X/O and winning/blocking tactic semantics.
2. Annotation contains the selected option-cell bbox.
3. Query ids are internal replay keys and do not define public task units.
4. `scalar_annotation_checked=true`
