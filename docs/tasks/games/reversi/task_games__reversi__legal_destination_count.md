# `task_games__reversi__legal_destination_count`

## Program Contract

- Domain: `games`
- Scene: `reversi`
- Public task id: `task_games__reversi__legal_destination_count`
- Supported `query_id` values: `single`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program schema: `count(legal_moves(current_player)); scene=reversi; scope=legal_destination_count`
- Program code: `count.reversi.legal_moves`
- Scalar annotation checked: `true`

## Generation Notes

- The task counts all legal empty destination cells for the current player.
- Annotation boxes are the board-cell bboxes for every counted destination cell.
- The answer and annotation are bound from the same generated legal-move set.
