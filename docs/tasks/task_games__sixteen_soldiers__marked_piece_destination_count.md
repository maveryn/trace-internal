# `task_games__sixteen_soldiers__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene: `sixteen_soldiers`
3. Scene id: `sixteen_soldiers`
4. Public task id: `task_games__sixteen_soldiers__marked_piece_destination_count`
5. Supported `query_id` values: `marked_piece_destination_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(adjacent_empty_destinations(x_marked_piece, drawn_line_graph)); scene=sixteen_soldiers; scope=marked_piece_destination_count`

## Generation Notes
1. The board is a fixed 37-point Sixteen Soldiers line graph with a 5 by 5 center and two triangular extensions.
2. A legal destination is an adjacent empty point connected to the piece marked with an X by one drawn line.
3. Annotation marks the centers of every legal empty destination point; an empty annotation list is valid when the answer is `0`.
