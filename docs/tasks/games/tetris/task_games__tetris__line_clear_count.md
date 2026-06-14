# `task_games__tetris__line_clear_count`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__line_clear_count`
5. Supported `query_id` values: `max_clear_with_next_piece`
6. Answer schema: `integer_count`
7. Annotation schema: `keyed_bbox_map`
8. Program schema: `value(arg_extreme(drop_options, metric=cleared_line_count(simulate_drop(board, next_piece, option)), direction=highest)); scene=tetris; scope=line_clear_count; query_branch=max_clear_with_next_piece`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
