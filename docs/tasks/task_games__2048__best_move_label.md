# `task_games__2048__best_move_label`

## Contract
1. Domain: `games`
2. Task group: `2048`
3. Scene id: `2048`
4. Query id: `best_move_label`
5. Objective: choose the labeled 2048 move that leaves the highest tile value in the outlined goal cell after one move.
6. Answer type: `string` option letter.
7. Evidence type: `bbox_set` over the original visible tile cells that form the selected move's goal-cell tile.

## Generation Notes
1. The scene shows four labeled candidate arrows and one outlined goal cell.
2. The answer is unique by construction: exactly one candidate move yields the largest positive value in the outlined cell.
3. Candidate labels are sampled from `A..H`, with four labels visible per instance.
4. Evidence stays pixel-grounded on the original source cells, not on the option label.
