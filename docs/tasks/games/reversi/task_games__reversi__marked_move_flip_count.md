# `task_games__reversi__marked_move_flip_count`

## Program Contract

- Domain: `games`
- Scene: `reversi`
- Public task id: `task_games__reversi__marked_move_flip_count`
- Supported `query_id` values: `single`
- Answer schema: `integer_count`
- Annotation schema: `point_set`
- Program schema: `count(flipped_discs(apply(marked_legal_move))); scene=reversi; scope=marked_move_flip_count`
- Program code: `count.transform.reversi_marked_move_flips`
- Scalar annotation checked: `true`

## Generation Notes

- The marked empty square is a legal Reversi move for the current player.
- The task asks how many opponent discs would flip if that marked move is played.
- Annotation points are the centers of all discs flipped by the marked move.
- The answer and annotation are bound from the same generated marked-move flip set.
