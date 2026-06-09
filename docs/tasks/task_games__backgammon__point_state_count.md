# `task_games__backgammon__point_state_count`

## Contract
1. Domain: `games`
2. Task group: `backgammon`
3. Scene id: `backgammon`
4. Public task id: `task_games__backgammon__point_state_count`
5. Supported `query_id` values: `black_single_checker_point_count`, `black_two_or_more_checker_point_count`, `white_single_checker_point_count`, `white_two_or_more_checker_point_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(numbered_backgammon_points(board_state), checker_color, stack_state)); scene=backgammon; scope=point_state_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from numbered point bboxes, not individual checker bboxes.
