# `task_games__sixteen_soldiers__marked_piece_destination_count`

## Program Contract

- Domain: `games`
- Scene: `sixteen_soldiers`
- Public task id: `task_games__sixteen_soldiers__marked_piece_destination_count`
- Supported `query_id` values: `single`
- Prompt query key: `marked_piece_destination_count`
- Answer schema: `integer_count`
- Annotation schema: `point_set`
- Program schema: `count(simple_adjacent_empty_destinations(x_marked_piece, drawn_line_graph)); scene=sixteen_soldiers; scope=marked_piece_destination_count`
- Program code: `count.sixteen_soldiers.marked_piece_destination`
- Scalar annotation checked: `true`

## Generation Notes

- The board is a fixed 37-point Sixteen Soldiers line graph with a 5 by 5 center and two triangular extensions.
- A simple-move destination is an adjacent empty point connected to the X-marked piece by one drawn line.
- Jump and capture landing points are excluded; captures are covered by `task_games__sixteen_soldiers__marked_piece_capture_count`.
- Annotation marks the centers of every simple-move destination point; an empty annotation list is valid when the answer is `0`.
- The answer and annotation are bound from the same generated board state.
