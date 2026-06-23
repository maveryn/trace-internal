# `task_games__sokoban__shortest_path_sequence_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__shortest_path_sequence_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_option(shortest_path_sequence); scene=sokoban; scope=shortest_path_sequence_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(shortest_path_sequence); scene=sokoban; scope=shortest_path_sequence_label`

## Generation Notes
1. The board shows walls, boxes, a start cell `S`, a goal cell `G`, and visible labeled move-sequence option panels.
2. Boxes are blockers for pathfinding.
3. Annotation is the scalar bbox of the selected option panel.
4. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
