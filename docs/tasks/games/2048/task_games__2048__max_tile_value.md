# `task_games__2048__max_tile_value`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/2048/`
3. Scene id: `2048`
4. Public task id: `task_games__2048__max_tile_value`
5. Supported `query_id` values: `single`
6. Prompt query key: `max_tile_value`
7. Answer schema: `integer_value`
8. Annotation schema: `bbox_set`
9. Program schema: `value(simulate(board, rules=slide_merge_2048, action=move_direction).final_board, property=max_tile_value); scene=2048; scope=max_tile_value`

## Program Contract
- `value(simulate(board, rules=slide_merge_2048, action=move_direction).final_board, property=max_tile_value); scene=2048; scope=max_tile_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
