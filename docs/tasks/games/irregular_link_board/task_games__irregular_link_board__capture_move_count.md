# `task_games__irregular_link_board__capture_move_count`

## Program Contract
- `count(filter(empty_points, predicate=legal_jump_capture_destination(marked_piece, occupied_points, drawn_links))); scene=irregular_link_board; scope=capture_move_count`

## Contract
- Domain: `games`
- Scene id: `irregular_link_board`
- Public task id: `task_games__irregular_link_board__capture_move_count`
- Supported `query_id` values: `single`
- Answer schema: `integer`
- Annotation schema: `point_set`

## Contract Notes
1. The board uses the same Fanorona/Alquerque-style base graph as the destination-count task: orthogonal links plus alternating diagonals, so diagonal lines do not cross unless the crossing is a playable point.
2. Public `query_id` is always `single`; the prompt template key remains `capture_move_count`.
3. A legal capture move jumps over one adjacent opposing piece along a straight drawn line and lands on the empty point immediately beyond it.
4. The capture task uses `5x5` and `6x6` boards so the answer support `0..8` is constructible.
5. Annotation marks the centers of every legal capture destination point, and an empty annotation list is valid when the answer is `0`.
