# `task_games__2048__merge_count`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/2048/`
3. Scene id: `2048`
4. Public task id: `task_games__2048__merge_count`
5. Supported `query_id` values: `single`
6. Prompt query key: `merge_count`
7. Answer schema: `integer_count`
8. Annotation schema: `point_pair_set`
9. Program schema: `count(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events); scene=2048; scope=merge_count`

## Program Contract
- `count(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events); scene=2048; scope=merge_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
4. Each annotation item is an unordered pair of point centers for the two original source tiles that merge; annotation cardinality equals the merge-count answer.
