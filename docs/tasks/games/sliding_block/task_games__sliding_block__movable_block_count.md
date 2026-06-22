# `task_games__sliding_block__movable_block_count`

## Contract
1. Domain: `games`
2. Scene id: `sliding_block`
3. Public task id: `task_games__sliding_block__movable_block_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(non_target_blocks_with_legal_one_cell_slide(board_state)); scene=sliding_block; scope=movable_block_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(non_target_blocks_with_legal_one_cell_slide(board_state)); scene=sliding_block; scope=movable_block_count`

## Generation Notes
1. Horizontal blocks slide horizontally and vertical blocks slide vertically.
2. A block is counted if at least one one-cell slide stays inside the board and does not overlap another block.
3. Annotation is the bbox set of all counted non-target blocks.

