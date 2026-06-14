# `task_games__tetris__drop_result_label`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__drop_result_label`
5. Supported `query_id` values: `multi_clear_result`, `no_clear_result`, `single_clear_result`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(select_option(drop_options, option_result = simulate_drop(board, piece, option))); scene=tetris; scope=drop_result_label; query_branch=multi_clear_result`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
