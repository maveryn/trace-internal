# `task_games__minigolf__shot_path_label`

## Contract
1. Domain: `games`
2. Scene id: `minigolf`
3. Public task id: `task_games__minigolf__shot_path_label`
4. Supported `query_id` values: `shot_path_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_pair_set`
7. Program schema: `label(select_option(shot_paths, option_rule=path_satisfies_target)); scene=minigolf; scope=shot_path_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
