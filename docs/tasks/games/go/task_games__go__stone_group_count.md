# `task_games__go__stone_group_count`

## Contract
1. Domain: `games`
2. Scene: `go`
2. Scene id: `go`
3. Public task id: `task_games__go__stone_group_count`
4. Supported `query_id` values: `black_stone_group_count`, `white_stone_group_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(connected_components(stones where color=query_color)); scene=go; scope=stone_group_count; query_color=black|white`

## Program Contract
- `count(connected_components(stones where color=query_color)); scene=go; scope=stone_group_count; query_color=black|white`

## Generation Notes
1. Query ids choose the counted stone color: black or white.
2. Annotation is one representative stone-center point for each counted connected group.
