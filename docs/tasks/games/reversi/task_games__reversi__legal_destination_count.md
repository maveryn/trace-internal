# `task_games__reversi__legal_destination_count`

## Program Contract

- Domain: `games`
- Scene: `reversi`
- Public task id: `task_games__reversi__legal_destination_count`
- Supported `query_id` values: `legal_move_count`, `corner_move_count`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program schema: `count(filter(legal_moves(current_player), destination_filter)); scene=reversi; scope=legal_destination_count`
- Program code: `count.filter.legal_moves.destination_filter`
- Scalar annotation checked: `true`

## Generation Notes

- `legal_move_count` counts all legal empty destination cells for the current player.
- `corner_move_count` uses the same legal-move rule, then filters to the four corner cells.
- Annotation boxes are the board-cell bboxes for every counted destination cell.
- The answer and annotation are bound from the same generated legal-move set.
