# `task_games__sliding_block__sliding_block_blocker_count`

## Contract
1. Domain: `games`
2. Scene id: `sliding_block`
3. Public task id: `task_games__sliding_block__sliding_block_blocker_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(blocks_intersecting(target_exit_path)); scene=sliding_block; scope=sliding_block_blocker_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(blocks_intersecting(target_exit_path)); scene=sliding_block; scope=sliding_block_blocker_count`

## Generation Notes
1. The red target block and exit arrow define the straight exit path.
2. The answer is the number of non-target blocks occupying cells on that path.
3. Annotation is the bbox set of the blocking blocks.

