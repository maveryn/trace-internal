# `task_games__radial_hunt_board__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene: `radial_hunt_board`
3. Scene id: `radial_hunt_board`
4. Public task id: `task_games__radial_hunt_board__marked_piece_destination_count`
5. Supported `query_id` values: `marked_piece_destination_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(empty_adjacent_points(linked_to(x_marked_piece))); scene=radial_hunt_board; scope=marked_piece_destination_count`

## Generation Notes
1. The board is a Pretwa-inspired radial graph with three concentric circles and three diameters, producing 19 playable points.
2. A legal destination is an adjacent empty point connected to the X-marked piece along one drawn circle or diameter segment.
3. Occupied adjacent points are not legal destinations.
4. The answer range is `0..6`; annotation marks the centers of every legal empty destination point, and an empty annotation list is valid when the answer is `0`.
