# `task_games__tetris__drop_collision_time_value`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__drop_collision_time_value`
5. Supported `query_id` values: `no_shift_collision_time`, `left_shift_collision_time`, `right_shift_collision_time`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set_map`

## Program Contract
`successful_downward_steps(simulate_horizontal_shift_then_vertical_drop(board, falling_piece, requested_shift)); scene=tetris; scope=drop_collision_time_value`

## Generation Notes
1. Query ids choose no shift, left shift, or right shift before the vertical drop.
2. A timestep is one successful downward move by one row; the failed collision move is not counted.
3. Annotation maps `start_piece` to the falling-piece cells and `stop_witness` to the locked cells that stop the shifted drop.
4. Scalar annotation checked: true.
