# `task_puzzles__sudoku__marked_cell_candidate_count`

## Program Contract
`count(candidate_digits(marked_cell, board_state)); scene=sudoku; scope=marked_cell_candidate_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `sudoku`
3. Public task id: `task_puzzles__sudoku__marked_cell_candidate_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set_map`

## Annotation
`annotation` is an object with:
- `marked_cell`: one image-pixel bbox for the marked empty cell.
- `constraint_cells`: image-pixel bboxes for visible filled peer cells that eliminate candidate digits.

## Generation Notes
The answer and annotation are bound from the same generated Sudoku board. Scene density, style, font, layout jitter, and target candidate count are generation/render metadata, not public query ids.
