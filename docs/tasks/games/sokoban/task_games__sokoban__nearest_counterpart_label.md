# `task_games__sokoban__nearest_counterpart_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__nearest_counterpart_label`
4. Supported `query_id` values: `nearest_target_for_marked_box_label`, `box_closest_to_marked_target_label`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_option(nearest_box_target_counterpart); scene=sokoban; scope=nearest_counterpart_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(nearest_box_target_counterpart); scene=sokoban; scope=nearest_counterpart_label`

## Generation Notes
1. The board shows labeled boxes, labeled targets, and option letters on candidate cells.
2. The task asks either for the target nearest to a marked box or the box nearest to a marked target by Manhattan distance.
3. Annotation is the scalar bbox of the selected option-marked cell.
4. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
