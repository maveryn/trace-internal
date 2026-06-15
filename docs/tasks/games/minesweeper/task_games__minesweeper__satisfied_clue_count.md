# `task_games__minesweeper__satisfied_clue_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__satisfied_clue_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Program Contract
`count(filter(opened_number_cells, adjacent_flag_count=clue_value)); scene=minesweeper; scope=satisfied_clue_count`

## Generation Notes
1. The scene includes both satisfied and unsatisfied opened number cells.
2. The answer counts only opened number cells whose clue equals their adjacent flag count.
3. Annotation boxes mark every counted opened clue cell.
