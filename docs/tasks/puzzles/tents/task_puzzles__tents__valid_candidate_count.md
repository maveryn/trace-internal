# `task_puzzles__tents__valid_candidate_count`

## Program Contract
`count(legal_tent_cells(marked_tree, candidate_cells, board_state, row_clues, col_clues)); scene=tents; scope=valid_candidate_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `tents`
3. Public task id: `task_puzzles__tents__valid_candidate_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Annotation
`annotation` is an array of image-pixel cell bounding boxes `[x0,y0,x1,y1]`, one for each legal labeled candidate cell. It is `[]` when no labeled candidate is legal.

## Generation Notes
The answer support is `0..4`, matching the four orthogonal neighbor candidates around the marked tree. The marked tree and clue rails are rule context but are not annotated for this count task.
