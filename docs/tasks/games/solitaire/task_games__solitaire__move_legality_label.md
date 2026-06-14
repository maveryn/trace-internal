# `task_games__solitaire__move_legality_label`

## Contract
1. Domain: `games`
2. Scene: `solitaire`
3. Scene id: `solitaire`
4. Public task id: `task_games__solitaire__move_legality_label`
5. Supported `query_id` values: `move_legality_label`
6. Answer schema: `string_label`
7. Annotation schema: `keyed_bbox_map`
8. Program schema: `label(move_legality(marked_move)); scene=solitaire; scope=move_legality_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
