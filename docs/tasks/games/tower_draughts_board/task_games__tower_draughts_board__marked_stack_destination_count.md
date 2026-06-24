# `task_games__tower_draughts_board__marked_stack_destination_count`

## Contract
1. Domain: `games`
2. Scene: `tower_draughts_board`
3. Scene id: `tower_draughts_board`
4. Public task id: `task_games__tower_draughts_board__marked_stack_destination_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract

`count(empty_playable_square for square in one_step_diagonal_destinations(x_marked_stack)); scene=tower_draughts_board; scope=marked_stack_destination_count`

## Generation Notes
1. The X-marked stack is controlled by the color of its top disk.
2. Regular top disks move one diagonal step forward; crowned top disks move one diagonal step in either direction.
3. Only empty playable squares are legal destinations.
4. The answer range is `0..4`.
5. Annotation marks the bounding box of every legal empty destination cell; an empty bbox set is valid when the answer is `0`.
