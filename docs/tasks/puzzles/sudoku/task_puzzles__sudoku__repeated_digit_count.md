# `task_puzzles__sudoku__repeated_digit_count`

## Program Contract
`count(repeated_digits(selected_unit, board_state)); scene=sudoku; scope=repeated_digit_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `sudoku`
3. Public task id: `task_puzzles__sudoku__repeated_digit_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Annotation
`annotation` is an array of image-pixel cell bboxes for highlighted-unit cells whose visible digit value repeats. It is `[]` when no digit repeats.

## Generation Notes
The highlighted unit type is sampled as generation metadata and is named in the prompt. The answer counts different repeated digit values, not annotation boxes.
