# `task_games__circular_chess__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene id: `circular_chess`
3. Public task id: `task_games__circular_chess__marked_piece_destination_count`
4. Supported `query_id` values: `marked_piece_move_count`, `marked_piece_capture_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(legal_destinations(marked_piece), destination_filter)); scene=circular_chess; scope=marked_piece_destination_count`

## Program Contract
- `count(filter(legal_destinations(marked_piece), destination_filter)); scene=circular_chess; scope=marked_piece_destination_count`

## Generation Notes
1. The scene uses a four-ring by sixteen-sector circular board with sector wraparound.
2. Pawns, check, checkmate, castling, en passant, and promotion are intentionally out of scope.
3. Annotation marks destination-cell centers as pixel-space points.
