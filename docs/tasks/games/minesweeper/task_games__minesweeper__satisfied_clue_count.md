# `task_games__minesweeper__satisfied_clue_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__satisfied_clue_count`
4. Supported `query_id` values: `satisfied_clue_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(numbered_clues, adjacent_flag_count(clue)=clue_value)); scene=minesweeper; scope=satisfied_clue_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
