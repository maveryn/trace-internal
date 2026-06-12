# `task_games__tower_draughts_board__marked_stack_capture_count`

## Contract
1. Domain: `games`
2. Scene: `tower_draughts_board`
3. Scene id: `tower_draughts_board`
4. Public task id: `task_games__tower_draughts_board__marked_stack_capture_count`
5. Supported `query_id` values: `marked_stack_capture_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(adjacent_opponent_stack for diagonal_jump in legal_immediate_captures(x_marked_stack)); scene=tower_draughts_board; scope=marked_stack_capture_count`

## Generation Notes
1. The X-marked stack is controlled by the color of its top disk.
2. A capture jumps diagonally over one adjacent opponent-controlled stack and lands on the empty playable square immediately beyond it.
3. Regular top disks capture forward only; crowned top disks capture in either diagonal direction.
4. The answer range is `0..4`.
5. Annotation marks the center point of every opponent-controlled stack that can be captured; an empty point set is valid when the answer is `0`.
