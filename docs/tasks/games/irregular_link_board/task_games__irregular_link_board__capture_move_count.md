# `task_games__irregular_link_board__capture_move_count`

## Contract
1. Domain: `games`
2. Scene id: `irregular_link_board`
3. Public task id: `task_games__irregular_link_board__capture_move_count`
5. Supported `query_id` values: `capture_move_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(empty_adjacent_points(linked_to(x_marked_piece) and capture_destination)); scene=irregular_link_board; scope=capture_move_count`

## Generation Notes
1. The board uses the same Fanorona/Alquerque-style base graph as the destination-count task: orthogonal links plus alternating diagonals, so diagonal lines do not cross unless the crossing is a playable point.
2. A legal move is a one-step move from the X-marked piece along a drawn link to an adjacent empty point.
3. A legal capture move jumps over one adjacent opposing piece along a straight drawn line and lands on the empty point immediately beyond it.
4. The capture task uses `5x5` and `6x6` boards so the answer support `0..8` is constructible.
5. Annotation marks the centers of every legal capture destination point, and an empty annotation list is valid when the answer is `0`.
