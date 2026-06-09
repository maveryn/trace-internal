# `task_games__tetris__drop_collision_time_value`

## Contract
1. Domain: `games`
2. Task group: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__drop_collision_time_value`
5. Supported `query_id` values: `no_shift_collision_time`, `left_shift_collision_time`, `right_shift_collision_time`
6. Answer schema: `integer_count`
7. Annotation schema: `keyed_bbox_set_map`
8. Program schema: `value(simulate_shifted_drop(board, falling_piece, horizontal_shift).successful_downward_steps); scene=tetris; scope=drop_collision_time_value`

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. The horizontal shift is applied first, with no rotation, then the piece falls vertically.
3. A timestep is one successful downward move by one row; the failed collision move is not counted.
4. Annotation maps `start_piece` to the visible falling-piece cells and `stop_witness` to the locked cells that stop the shifted drop.
