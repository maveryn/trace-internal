# `task_games__go__marked_group_stone_count`

## Contract
1. Domain: `games`
2. Scene: `go`
2. Scene id: `go`
3. Public task id: `task_games__go__marked_group_stone_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(connected_group(marked_stone)); scene=go; scope=marked_group_stone_count`

## Program Contract
- `count(connected_group(marked_stone)); scene=go; scope=marked_group_stone_count`

## Generation Notes
1. The scene draws one red outline around a single black or white reference stone.
2. The answer is the number of same-color stones connected edge-to-edge to that marked stone, including the marked stone.
3. Annotation is the stone box for every stone in the marked stone's connected group.
4. Group-size answers are sampled from `2..6`.
