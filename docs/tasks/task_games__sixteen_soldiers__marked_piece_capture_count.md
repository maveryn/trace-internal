# `task_games__sixteen_soldiers__marked_piece_capture_count`

## Contract
1. Domain: `games`
2. Task group: `sixteen_soldiers`
3. Scene id: `sixteen_soldiers`
4. Public task id: `task_games__sixteen_soldiers__marked_piece_capture_count`
5. Supported `query_id` values: `marked_piece_capture_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(immediate_jump_captures(x_marked_piece, drawn_line_graph)); scene=sixteen_soldiers; scope=marked_piece_capture_count`

## Generation Notes
1. The board is a fixed 37-point Sixteen Soldiers line graph with a 5 by 5 center and two triangular extensions.
2. A capture is counted only when the X-marked piece can jump in one drawn straight line over an adjacent opponent piece and land on the empty point immediately beyond.
3. Annotation marks the centers of capturable opponent pieces. Landing points are included in trace metadata for verifier/debugging, but are not prompt-facing annotation.
