# `task_games__tetris__edge_occupied_row_cell_count`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__edge_occupied_row_cell_count`
5. Supported `query_id` values: `top_occupied_row_filled_cell_count`, `top_occupied_row_empty_cell_count`, `bottom_occupied_row_filled_cell_count`, `bottom_occupied_row_empty_cell_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(cells in edge_occupied_row(board, requested_edge) where occupancy(cell) = requested_status); scene=tetris; scope=edge_occupied_row_cell_count`

## Generation Notes
1. Query ids choose the top or bottom occupied row and whether filled or empty cells are counted.
2. Annotation marks the counted cell bboxes in the selected occupied row.
3. Scalar annotation checked: true.
