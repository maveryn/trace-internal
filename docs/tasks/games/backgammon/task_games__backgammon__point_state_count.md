# `task_games__backgammon__point_state_count`

## Contract
1. Domain: `games`
2. Scene id: `backgammon`
3. Public task id: `task_games__backgammon__point_state_count`
4. Supported `query_id` values: `black_single_checker_point_count`, `white_single_checker_point_count`, `black_two_or_more_checker_point_count`, `white_two_or_more_checker_point_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(numbered_backgammon_points(board_state), checker_color, stack_state)); scene=backgammon; scope=point_state_count`

## Program Contract
- `count(filter(numbered_backgammon_points(board_state), checker_color, stack_state)); scene=backgammon; scope=point_state_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from numbered point bboxes, not individual checker bboxes.
