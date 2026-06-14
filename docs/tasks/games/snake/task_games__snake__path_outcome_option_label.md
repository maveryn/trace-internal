# `task_games__snake__path_outcome_option_label`

## Contract
1. Domain: `games`
2. Scene: `snake`
3. Scene id: `snake`
4. Public task id: `task_games__snake__path_outcome_option_label`
5. Supported `query_id` values: `path_result_option_label`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox_set`
8. Program schema: `label(select_option(path_options, option_path_result = simulate_path(snake_state, path_option))); scene=snake; scope=path_outcome_option_label; query_branch=path_result_option_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
