# `task_games__tetris__drop_result_label`

1. Domain: `games`
2. Scene id: `tetris`
3. Public task id: `task_games__tetris__drop_result_label`
4. Answer type: string option label
5. Evidence: `bbox_set` containing the selected result-board bounding box.

The scene shows a START Tetris board with the falling piece drawn at the top in its current column and orientation, plus five labeled result boards. The piece falls straight down without moving sideways or rotating. The options show final locked board states only, with no falling piece.

Internal query ids are `no_clear_result`, `single_clear_result`, and `multi_clear_result`.

Current generation samples board sizes from 7..11 columns by 10..15 rows. Rendering combines shared games panel backgrounds, layout jitter, sampled fonts, post-image noise, and five scene-local tetromino block styles.
