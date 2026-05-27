# `task_games__snake__path_outcome_option_label`

## Contract
1. Domain: `games`
2. Task group: `snake`
3. Scene id: `snake`
4. Query id: `path_result_option_label`
5. Prompt bundle: `games_snake_v0`
6. Evidence type: `bbox_set`
7. Answer type: `option_letter`

## Query Notes
1. `path_result_option_label` asks the model to follow a listed sequence of 3 to 5 moves.
2. The image shows four labeled result options: three marked point cells and one `GAME OVER` card. The answer is the visible option letter.
3. `GAME OVER` is correct when the snake hits the board edge, its own body, or a gray wall cell before completing the sequence.
4. Evidence boxes mark the in-board cells traversed by the head until the result. For an off-board hit, evidence uses the visible path cells up to the board edge.

## Generation Notes
The sampler builds a connected visible snake, places gray wall cells, searches for a move sequence with the target result, and renders the four answer options directly in the image. Game-over targets are sampled at roughly 25% by default.
