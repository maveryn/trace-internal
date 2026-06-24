# `task_games__sokoban__box_goal_status_count`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__box_goal_status_count`
4. Supported `query_id` values: `box_on_goal_count`, `box_off_goal_count`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count_boxes_by_matching_goal_status(status=on_goal|off_goal); scene=sokoban; scope=box_goal_status_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count_boxes_by_matching_goal_status(status=on_goal|off_goal); scene=sokoban; scope=box_goal_status_count`

## Generation Notes
1. The board shows paired colored boxes and matching colored goal dots.
2. The task asks either for boxes on their matching colored goal dots or boxes not on their matching colored goal dots.
3. The answer is an integer from `0` to `5`.
4. Annotation is the bbox set of the counted box cells; cardinality equals the answer.
5. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
