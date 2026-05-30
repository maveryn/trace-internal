# `task_games__ultimate_tictactoe__local_tactic_label`

1. Domain: `games`
2. Scene id: `ultimate_tictactoe`
3. Public task id: `task_games__ultimate_tictactoe__local_tactic_label`
4. Query ids: `x_winning_move_label`, `o_winning_move_label`, `x_blocking_move_label`, `o_blocking_move_label`

## Contract

The image shows an Ultimate Tic-Tac-Toe board with one highlighted small board. Empty cells in that highlighted board are labeled as answer options. The task asks for the winning or blocking move label.

Evidence is a `bbox_set` containing the selected empty-cell option box plus the two supporting threat or winning-line cells. The answer is a single option letter.

## Notes

Rendering combines shared games panel backgrounds, layout jitter, unit-size jitter, sampled fonts, post-image noise, and five scene-local board styles. Candidate letters are drawn inside empty cells on the highlighted small board.

Prompt bundle: `games_ultimate_tictactoe_v0`.
