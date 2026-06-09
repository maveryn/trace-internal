# `task_games__tetris__edge_occupied_row_cell_count`

## Contract
1. Domain: `games`
2. Task group: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__edge_occupied_row_cell_count`
5. Supported `query_id` values: `top_occupied_row_filled_cell_count`, `top_occupied_row_empty_cell_count`, `bottom_occupied_row_filled_cell_count`, `bottom_occupied_row_empty_cell_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(cells(edge_occupied_row(board, edge)), occupancy(cell) = requested_status)); scene=tetris; scope=edge_occupied_row_cell_count`

## Generation Notes
1. Query ids choose the row edge (`top` or `bottom`) and counted cell status (`filled` or `empty`).
2. Annotation marks the counted cell bounding boxes in the selected edge occupied row.
3. Boards use the supported-stack construction policy so locked cells do not float without vertical support.
