# `task_games__hex__winning_move_cell_label`

## Contract
1. Domain: `games`
2. Task group: `hex`
3. Scene id: `hex`
4. Query id: `winning_move_cell_label`
5. Objective: choose the labeled empty Hex cell that lets the queried player win immediately.
6. Answer type: `string`, one candidate label such as `A`.
7. Evidence type: `bbox_set` over the cells in the completed winning chain after the move, including the chosen labeled cell.

## Generation Notes
1. Red connects the left and right red sides.
2. Blue connects the top and bottom blue sides.
3. The board is generated with exactly one immediate winning empty cell for the queried player.
4. Candidate labels are shuffled over empty cells, and the answer label is unique by construction.
