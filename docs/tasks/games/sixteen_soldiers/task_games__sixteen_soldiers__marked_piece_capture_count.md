# `task_games__sixteen_soldiers__marked_piece_capture_count`

## Program Contract

- Domain: `games`
- Scene: `sixteen_soldiers`
- Public task id: `task_games__sixteen_soldiers__marked_piece_capture_count`
- Supported `query_id` values: `single`
- Prompt query key: `marked_piece_capture_count`
- Answer schema: `integer_count`
- Annotation schema: `point_set`
- Program schema: `count(immediate_jump_captures(x_marked_piece, drawn_line_graph)); scene=sixteen_soldiers; scope=marked_piece_capture_count`
- Program code: `count.sixteen_soldiers.marked_piece_capture`
- Scalar annotation checked: `true`

## Generation Notes

- The board is a fixed 37-point Sixteen Soldiers line graph with a 5 by 5 center and two triangular extensions.
- A capture is counted only when the X-marked piece can jump in one drawn straight line over an adjacent opponent piece and land on the empty point immediately beyond.
- Annotation marks the centers of capturable opponent pieces. Landing points remain in trace metadata for verifier/debugging, but are not prompt-facing annotation.
- The answer and annotation are bound from the same generated board state.
