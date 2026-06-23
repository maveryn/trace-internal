# `task_games__sokoban__path_validity_sequence_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__path_validity_sequence_label`
4. Supported `query_id` values: `valid_path_sequence_label`, `blocked_path_sequence_label`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_option(path_sequence_validity); scene=sokoban; scope=path_validity_sequence_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(path_sequence_validity); scene=sokoban; scope=path_validity_sequence_label`

## Generation Notes
1. The board shows walls, boxes, a start cell `S`, a goal cell `G`, and visible labeled move-sequence option panels.
2. The task asks for either a valid route or a blocked route using the same answer and annotation schema.
3. Annotation is the scalar bbox of the selected option panel.
4. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.
