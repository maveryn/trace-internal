# `task_games__tower_draughts_board__controlled_stack_count`

## Contract
1. Domain: `games`
2. Scene: `tower_draughts_board`
3. Scene id: `tower_draughts_board`
4. Public task id: `task_games__tower_draughts_board__controlled_stack_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract

`count(stack for stack in visible_stacks if top_disk_color == target_player); scene=tower_draughts_board; scope=controlled_stack_count`

## Generation Notes
1. The board uses alternating playable squares with stacks of red and black disks.
2. A stack is controlled by the color of its top disk; lower disks are visible distractors.
3. The answer range is `0..10`.
4. Annotation marks the bounding box of every stack controlled by the target player; an empty bbox set is valid when the answer is `0`.
