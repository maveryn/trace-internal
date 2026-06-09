# `task_games__go__stone_group_count`

## Contract
1. Domain: `games`
2. Task group: `go`
3. Scene id: `go`
4. Public task id: `task_games__go__stone_group_count`
5. Supported `query_id` values: `black_stone_group_count`, `white_stone_group_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(connected_components(stones where color=query_color)); scene=go; scope=stone_group_count`

## Generation Notes
1. This task follows the taxonomy-v0 public task-id form.
2. Query ids choose the counted stone color and do not define public task units.
3. Annotation is one representative stone-center point for each counted connected group.
