# `task_games__tetris__active_piece_shape_label`

## Contract
1. Domain: `games`
2. Scene: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__active_piece_shape_label`
5. Supported `query_id` values: `single`
6. Answer schema: `string_label`
7. Annotation schema: `bbox`

## Program Contract
`shape_label(active_falling_tetromino); scene=tetris; scope=active_piece_shape_label`

## Generation Notes
1. The renderer shows a Tetris board with one active falling piece and a visual legend of the seven tetromino labels.
2. The answer is the tetromino label `I`, `O`, `T`, `L`, `J`, `S`, or `Z`.
3. Annotation is the scalar bbox enclosing the falling-piece cells on the board.
4. Scalar annotation checked: true.
