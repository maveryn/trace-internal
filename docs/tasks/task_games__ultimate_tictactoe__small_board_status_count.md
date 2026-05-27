# `task_games__ultimate_tictactoe__small_board_status_count`

1. Domain: `games`
2. Scene id: `ultimate_tictactoe`
3. Source task group: `ultimate_tictactoe`
4. Public query id: `default`
5. Query ids: `x_won_board_count`, `o_won_board_count`, `neither_won_board_count`, `drawn_board_count`

## Contract

The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. The task asks for a count of small boards with a specified status.

Evidence is a `bbox_set` containing the matching small-board boxes. The answer is an integer count.

## Notes

Prompt bundle: `games_ultimate_tictactoe_v0`.
