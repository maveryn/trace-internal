# `task_games__hex__winning_move_cell_label`

## Contract
1. Domain: `games`
2. Scene: `hex`
3. Scene id: `hex`
4. Public task id: `task_games__hex__winning_move_cell_label`
5. Supported `query_id` values: `single`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(filter(labeled_empty_cells, move_result=connects_player_sides)); scene=hex; scope=winning_move_cell_label`

## Program Contract
- `label(filter(labeled_empty_cells, move_result=connects_player_sides)); scene=hex; scope=winning_move_cell_label`

## Generation Notes
1. `query_id=single` is the public no-branch query id; the prompt uses the Hex winning-move template.
2. Candidate labels are rendered in the image and the answer is the one label that wins immediately.
3. Annotation is one point at the center of the winning candidate cell.
