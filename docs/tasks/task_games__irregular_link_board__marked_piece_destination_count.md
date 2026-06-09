# `task_games__irregular_link_board__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Task group: `irregular_link_board`
3. Scene id: `irregular_link_board`
4. Public task id: `task_games__irregular_link_board__marked_piece_destination_count`
5. Supported `query_id` values: `marked_piece_destination_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(empty_adjacent_points(linked_to(x_marked_piece))); scene=irregular_link_board; scope=marked_piece_destination_count`

## Generation Notes
1. The board is a variable-size point lattice with a Fanorona/Alquerque-style base graph: orthogonal links plus alternating diagonals, so diagonal lines do not cross unless the crossing is a playable point.
2. A legal destination is an adjacent empty point connected to the X-marked piece by a drawn link.
3. Adjacent occupied points and adjacent points without a drawn link are not legal destinations.
4. The answer range is `0..8`; annotation marks the centers of every legal empty destination point, and an empty annotation list is valid when the answer is `0`.
