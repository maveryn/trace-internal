# `task_games__snake__path_outcome_option_label`

## Contract
1. Domain: `games`
2. Scene id: `snake`
3. Public task id: `task_games__snake__path_outcome_option_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_set`
7. Program schema: `selection.option_value_match(simulate_snake_move_sequence, visible_result_options); scene=snake; scope=path_outcome_option_label`
8. Scalar annotation checked: `true`

## Program Contract
- `selection.option_value_match(simulate_snake_move_sequence, visible_result_options); scene=snake; scope=path_outcome_option_label`

## Generation Notes
1. Simulate the listed moves in order. The answer is the visible option label for the final head cell or `GAME OVER`.
2. Annotation is the bbox set for visible in-board cells traversed by the head up to the result.
3. The image always shows options `A` through `D`, with one `GAME OVER` option card.
4. Prompt wording comes from `prompts/games/snake/games_snake_v1.json`.
