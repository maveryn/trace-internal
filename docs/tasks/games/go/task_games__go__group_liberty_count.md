# `task_games__go__group_liberty_count`

## Contract
1. Domain: `games`
2. Scene id: `go`
3. Public task id: `task_games__go__group_liberty_count`
4. Supported `query_id` values: `marked_group_liberty_count`, `marked_group_shared_liberty_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(liberties(marked_group), liberty_filter)); scene=go; scope=group_liberty_count; query_branch=marked_group_liberty_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
