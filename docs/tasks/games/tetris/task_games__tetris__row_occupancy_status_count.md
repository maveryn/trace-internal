# `task_games__tetris__row_occupancy_status_count`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__row_occupancy_status_count`
5. Supported `query_id` values: `full_row_count`, `one_gap_row_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(rows where row_occupancy_status(row) = requested_status); scene=tetris; scope=row_occupancy_status_count`

## Generation Notes
1. Query ids choose the requested row status: full or exactly one empty cell.
2. Annotation marks whole qualifying row bboxes on the rendered board.
3. Scalar annotation checked: true.
