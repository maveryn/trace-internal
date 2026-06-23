# `task_games__tetris__line_clear_count`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__line_clear_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_map`

## Program Contract
`max(cleared_row_count(simulate_drop(board, rotate_translate(next_piece, placement)))) over legal placements; scene=tetris; scope=line_clear_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation maps `board` and `next_piece` to the rendered board and NEXT-piece preview boxes.
3. Scalar annotation checked: true.
