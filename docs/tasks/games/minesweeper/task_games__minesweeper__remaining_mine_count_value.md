# `task_games__minesweeper__remaining_mine_count_value`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__remaining_mine_count_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `point`

## Program Contract
`difference(clue_value(marked_clue), adjacent_flag_count(marked_clue)); scene=minesweeper; scope=marked_clue_remaining_mine_count`

## Generation Notes
1. The scene marks exactly one opened clue cell.
2. The answer is how many additional adjacent mines are still needed by that marked clue.
3. Annotation is the scalar point at the center of the marked opened clue cell.
