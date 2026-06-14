# `task_puzzles__sudoku__repeated_digit_count`

## Contract
1. Domain: `puzzles`
2. Scene: `sudoku`
3. Scene id: `sudoku`
4. Public task id: `task_puzzles__sudoku__repeated_digit_count`
5. Supported `query_id` values: `repeated_digit_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(repeated_digits(selected_unit)); scene=sudoku; scope=repeated_digit_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated puzzle state used for answer verification.
