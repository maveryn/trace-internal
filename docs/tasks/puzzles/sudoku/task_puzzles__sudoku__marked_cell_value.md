# `task_puzzles__sudoku__marked_cell_value`

## Contract
1. Domain: `puzzles`
2. Scene: `sudoku`
3. Scene id: `sudoku`
4. Public task id: `task_puzzles__sudoku__marked_cell_value`
5. Supported `query_id` values: `marked_cell_value`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `value(single(candidate_digits(marked_cell, board_state))); scene=sudoku; scope=marked_cell_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated puzzle state used for answer verification.
