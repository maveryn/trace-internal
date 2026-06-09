# `task_games__chess__checkmate_move_label`

## Contract
1. Domain: `games`
2. Task group: `chess`
3. Scene id: `chess`
4. Public task id: `task_games__chess__checkmate_move_label`
5. Supported `query_id` values: `checkmate_move_label`
6. Answer schema: `option_letter`
7. Annotation schema: `keyed_bbox_map`
8. Program schema: `select(option where move_checkmates(opponent_king)); scene=chess; scope=checkmate_move_label`

## Generation Notes
1. The board shows standard chess coordinates on the margins and a visible panel of candidate moves.
2. The visible options are encoded as piece name plus source and destination square.
3. Exactly one displayed option is an immediate checkmate by construction; the underlying board may contain other mating moves that are not displayed.
4. Annotation is projected from the selected move's source square, destination square, and opposing king square using keys `from`, `to`, and `king`.
