# `task_games__sokoban__closest_box_goal_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__closest_box_goal_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_closest_box_by_matching_goal(boxes, matching_goals, distance=manhattan); scene=sokoban; scope=closest_box_goal_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_closest_box_by_matching_goal(boxes, matching_goals, distance=manhattan); scene=sokoban; scope=closest_box_goal_label`

## Generation Notes
1. The board shows lettered colored boxes and matching colored goal dots.
2. No box starts on its matching goal.
3. The task asks which labeled box is closest to its matching colored goal dot.
4. Distance is Manhattan grid distance: row steps plus column steps. Walls do not change the distance.
5. The closest box is unique by construction.
6. Annotation is the scalar bbox of the selected box cell.
7. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
