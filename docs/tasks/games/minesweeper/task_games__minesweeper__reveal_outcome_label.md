# `task_games__minesweeper__reveal_outcome_label`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__reveal_outcome_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `keyed_point_set_map`

## Program Contract
`select(option where option_value=reveal_outcome(marked_hidden_cell)); scene=minesweeper; scope=reveal_outcome_label`

## Generation Notes
1. The scene marks one hidden cell and shows 4 or 6 visible reveal-result options.
2. Exactly one option matches whether the marked cell would reveal a mine, empty cell, or number.
3. Annotation keys are `target_cell`, `supporting_clues`, and `supporting_flags`, each mapped to cell-center points.
