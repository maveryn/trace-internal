# `task_games__sliding_block__sliding_block_move_result_label`

## Contract
1. Domain: `games`
2. Scene id: `sliding_block`
3. Public task id: `task_games__sliding_block__sliding_block_move_result_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_set`
7. Program schema: `select(option_board_equal_to(apply_ordered_slides(source_board, slide_sequence))); scene=sliding_block; scope=sliding_block_move_result_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select(option_board_equal_to(apply_ordered_slides(source_board, slide_sequence))); scene=sliding_block; scope=sliding_block_move_result_label`

## Generation Notes
1. The prompt gives a short ordered slide sequence.
2. The answer is the visual option label whose board matches the final state.
3. Annotation is the bbox set containing moved source blocks plus the correct option panel.

