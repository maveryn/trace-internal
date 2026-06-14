# `task_games__tic_tac_toe_3d__winning_move_cell_label`

## Contract
1. Domain: `games`
2. Scene: `tic_tac_toe_3d`
3. Scene id: `tic_tac_toe_3d`
4. Public task id: `task_games__tic_tac_toe_3d__winning_move_cell_label`
5. Supported `query_id` values: `o_winning_move_label`, `x_winning_move_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(filter(candidate_cells, completes_3d_tic_tac_toe_line(player, cell)=True)); scene=tic_tac_toe_3d; scope=winning_move_cell_label`

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. The board is a 3 by 3 by 3 Tic-Tac-Toe state with one correct labeled empty-cell option by construction.
3. Annotation is projected from the selected empty cell and the two visible same-player cells that support the winning line.
