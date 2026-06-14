# `task_games__match3__target_clear_swap_label`

## Contract
1. Domain: `games`
2. Scene id: `match3`
3. Public task id: `task_games__match3__target_clear_swap_label`
4. Supported `query_id` values: `target_clear_swap_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_set`
7. Program schema: `label(select_option(swap_options, option_value=target_clear_count, option_metric=cleared_count_after_swap(option))); scene=match3; scope=target_clear_swap_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
