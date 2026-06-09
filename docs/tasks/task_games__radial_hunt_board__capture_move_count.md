# `task_games__radial_hunt_board__capture_move_count`

## Contract
1. Domain: `games`
2. Task group: `radial_hunt_board`
3. Scene id: `radial_hunt_board`
4. Public task id: `task_games__radial_hunt_board__capture_move_count`
5. Supported `query_id` values: `capture_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(empty_landing_points(capture_jump_from(x_marked_piece))); scene=radial_hunt_board; scope=capture_move_count`

## Generation Notes
1. The board is a Pretwa-inspired radial graph with three concentric circles and three diameters, producing 19 playable points.
2. A legal capture move jumps over one adjacent opposing piece along the same drawn circle or diameter line and lands on the empty point immediately beyond it.
3. The task does not use compulsory capture, multi-capture continuation, or win/loss conditions.
4. The answer range is `0..6`; annotation marks the centers of every legal capture landing point, and an empty annotation list is valid when the answer is `0`.
