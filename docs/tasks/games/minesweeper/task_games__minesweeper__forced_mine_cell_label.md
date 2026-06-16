# `task_games__minesweeper__forced_mine_cell_label`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__forced_mine_cell_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `point`

## Program Contract
`select(label for hidden option cell where forced_status(cell)=mine); scene=minesweeper; scope=forced_mine_option_label`

## Generation Notes
1. The scene shows exactly four labeled hidden cells, `A` through `D`.
2. Exactly one labeled hidden cell is guaranteed to be a mine by the visible clue information.
3. The answer is the option letter printed inside that hidden cell.
4. Annotation is the scalar point at the center of the correct labeled hidden cell.
