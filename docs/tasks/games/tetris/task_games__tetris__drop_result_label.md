# `task_games__tetris__drop_result_label`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__drop_result_label`
5. Supported `query_id` values: `no_clear_result`, `single_clear_result`, `multi_clear_result`
6. Answer schema: `string_label`
7. Annotation schema: `bbox`

## Program Contract
`label(option where option.board = simulate_fixed_drop(board, falling_piece, line_clear_rules)); scene=tetris; scope=drop_result_label`

## Generation Notes
1. Query ids choose whether the fixed drop clears zero, one, or multiple rows.
2. The renderer always shows exactly four labeled result-board options in a two-by-two grid below the START board.
3. Annotation is the scalar bbox of the selected result-board option panel.
4. Scalar annotation checked: true.
