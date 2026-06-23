# `task_games__sliding_block__block_orientation_count`

## Contract
1. Domain: `games`
2. Scene id: `sliding_block`
3. Public task id: `task_games__sliding_block__block_orientation_count`
4. Supported `query_id` values: `horizontal_block_count`, `vertical_block_count`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(blocks_matching_orientation(board_state, requested_orientation)); scene=sliding_block; scope=block_orientation_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(blocks_matching_orientation(board_state, requested_orientation)); scene=sliding_block; scope=block_orientation_count`

## Generation Notes
1. The board has no target block or exit arrow for this task.
2. `horizontal_block_count` counts blocks wider than they are tall.
3. `vertical_block_count` counts blocks taller than they are wide.
4. Annotation is the bbox set of all blocks matching the requested orientation.
