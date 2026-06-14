# `task_games__2048__score_value`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/2048/`
3. Scene id: `2048`
4. Public task id: `task_games__2048__score_value`
5. Supported `query_id` values: `single`
6. Prompt query key: `score_value`
7. Answer schema: `integer_value`
8. Annotation schema: `point_pair_set`
9. Program schema: `sum(values(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events, metric=created_tile_value)); scene=2048; scope=score_value`

## Program Contract
- `sum(values(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events, metric=created_tile_value)); scene=2048; scope=score_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
4. Each annotation item is an unordered pair of point centers for the two original source tiles in one merge contributing to the score.
