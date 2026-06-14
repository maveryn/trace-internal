# `task_games__bowling__spare_path_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/bowling/`
3. Scene id: `bowling`
4. Public task id: `task_games__bowling__spare_path_label`
5. Supported `query_id` values: `spare_path_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_pair_set`
8. Program schema: `label(select_option(shot_paths, option_rule=clears_remaining_pins)); scene=bowling; scope=spare_path_label`

## Program Contract
- `label(select_option(shot_paths, option_rule=clears_remaining_pins)); scene=bowling; scope=spare_path_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
