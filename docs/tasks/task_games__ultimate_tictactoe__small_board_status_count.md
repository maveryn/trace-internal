# `task_games__ultimate_tictactoe__small_board_status_count`

1. Domain: `games`
2. Scene id: `ultimate_tictactoe`
3. Public task id: `task_games__ultimate_tictactoe__small_board_status_count`
4. Query ids: `x_won_board_count`, `o_won_board_count`, `neither_won_board_count`, `drawn_board_count`

## Contract

The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. The task asks for a count of small boards with a specified status.

Evidence is a `bbox_set` containing the matching small-board boxes. The answer is an integer count.

## Notes

Rendering combines shared games panel backgrounds, layout jitter, unit-size jitter, sampled fonts, post-image noise, and five scene-local board styles. Winning lines are not pre-drawn; the model must inspect the X/O marks.

Prompt bundle: `games_ultimate_tictactoe_v0`.
