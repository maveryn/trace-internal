# `task_games__minesweeper__forced_cell_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__forced_cell_count`
4. Supported `query_id` values: `forced_mine_count`, `forced_safe_count`
5. Answer schema: `integer`
6. Annotation schema: `point_set`

## Program Contract
`count(filter(hidden_cells, forced_status in {mine,safe})); scene=minesweeper; scope=forced_cell_count`

## Generation Notes
1. The scene shows a visible Minesweeper board with opened number cells, hidden cells, and flags.
2. The query branch selects whether to count hidden cells forced to be mines or forced to be safe.
3. Annotation points mark the centers of every counted hidden cell.
