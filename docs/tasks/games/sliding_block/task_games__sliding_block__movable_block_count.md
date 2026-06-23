# `task_games__sliding_block__movable_block_count`

## Contract
1. Domain: `games`
2. Scene id: `sliding_block`
3. Public task id: `task_games__sliding_block__movable_block_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(blocks_with_legal_one_cell_slide_along_orientation(board_state)); scene=sliding_block; scope=movable_block_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(blocks_with_legal_one_cell_slide_along_orientation(board_state)); scene=sliding_block; scope=movable_block_count`

## Generation Notes
1. The board has no target block for this task.
2. Horizontal blocks slide horizontally and vertical blocks slide vertically.
3. A block is counted if at least one one-cell slide stays inside the board and does not overlap another block.
4. Annotation is the bbox set of all counted blocks.
