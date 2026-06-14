# `task_games__minesweeper__forced_cell_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__forced_cell_count`
4. Supported `query_id` values: `forced_mine_count`, `forced_safe_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(hidden_cells, forced_status=forced_cell_status)); scene=minesweeper; scope=forced_cell_count; query_branch=forced_mine_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
