# `task_games__tetris__line_clear_count`

1. Domain: `games`
2. Scene id: `tetris`
3. Public task id: `task_games__tetris__line_clear_count`
4. Answer type: integer
5. Evidence: `bbox_set` over the main board and NEXT piece panel.

The scene shows a Tetris board with colored locked blocks and a NEXT piece panel above it. The task asks for the maximum number of rows the next piece can clear if it may be translated sideways and rotated before falling.

Current generation samples row-clear answers from `0..4` and board sizes from 7..11 columns by 10..15 rows.
