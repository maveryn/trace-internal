# `task_games__sokoban__push_stand_cell_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__push_stand_cell_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_player_stand_cell_for_straight_push(box, matching_goal, candidate_stand_cells); scene=sokoban; scope=push_stand_cell_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_player_stand_cell_for_straight_push(box, matching_goal, candidate_stand_cells); scene=sokoban; scope=push_stand_cell_label`

## Generation Notes
1. The board shows a player, colored boxes, matching colored goal dots, and four labeled candidate standing cells around one target box.
2. The prompt names the target box by a canonical safe color label from `trace.tasks.shared.named_colors`.
3. The target goal is in a straight horizontal or vertical line from the target box.
4. There are no walls, boxes, or other objects between the target box and its matching goal dot.
5. The correct stand cell is the labeled cell immediately behind the target box, opposite the push direction toward the goal.
6. Annotation is the scalar bbox of the selected stand cell.
7. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
