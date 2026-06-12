# `task_games__nine_mens_morris__mill_completion_point_count`

## Contract
1. Domain: `games`
2. Scene id: `nine_mens_morris`
3. Public task id: `task_games__nine_mens_morris__mill_completion_point_count`
4. Supported `query_id` values: `black_mill_completion_point_count`, `white_mill_completion_point_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(empty_board_points, completes_mill(point, queried_color))); scene=nine_mens_morris; scope=mill_completion_point_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks empty board points where placing one queried-color piece would complete at least one mill.
