# `task_puzzles__tents__missing_tent_cell_label`

## Program Contract
`label(single(legal_tent_cells(marked_tree, board_state, row_clues, col_clues))); scene=tents; scope=missing_tent_cell_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `tents`
3. Public task id: `task_puzzles__tents__missing_tent_cell_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`

## Annotation
`annotation` is one image-pixel bounding box `[x0,y0,x1,y1]` for the selected labeled candidate cell.

## Generation Notes
The generated board has exactly one legal labeled candidate for the marked tree. Candidate label assignment, grid size, scene variant, palette, and background style are generation/render metadata, not public query ids.
