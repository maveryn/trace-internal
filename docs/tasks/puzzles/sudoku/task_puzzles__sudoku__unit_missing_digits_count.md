# `task_puzzles__sudoku__unit_missing_digits_count`

## Program Contract
`count(missing_digits(selected_unit, board_state)); scene=sudoku; scope=unit_missing_digits_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `sudoku`
3. Public task id: `task_puzzles__sudoku__unit_missing_digits_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Annotation
`annotation` is an array of image-pixel cell bboxes for visible filled cells in the highlighted row, column, or 3 by 3 box.

## Generation Notes
The highlighted unit type is sampled as generation metadata and is named in the prompt. The answer counts missing digit values, not annotation boxes.
