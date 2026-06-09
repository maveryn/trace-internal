# `task_games__sliding_block__sliding_block_move_result_label`

## Summary
1. Domain: `games`
2. Task group: `sliding_block`
3. Task id: `task_games__sliding_block__sliding_block_move_result_label`
4. Scene id: `sliding_block`
5. Goal: apply a short ordered sequence of sliding-block moves and select the final board option.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `move_result_label`
3. Board size: `6..8` rows by `6..8` columns
4. Move count: `1..2`
5. Answer label support: `A..F`
6. Answer type: `option_letter`
7. Annotation type: `bbox_set`
8. Annotation target: original boxes of the moved blocks in first-seen move order, followed by the correct final-board option panel box
9. Scene variants: `wooden_tray|cool_grid|paper_board`
