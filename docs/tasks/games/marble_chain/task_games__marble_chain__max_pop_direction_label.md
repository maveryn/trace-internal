# `task_games__marble_chain__max_pop_direction_label`

## Contract
1. Domain: `games`
2. Scene id: `marble_chain`
3. Public task id: `task_games__marble_chain__max_pop_direction_label`
4. Supported `query_id` values: `max_pop_direction_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_set`
7. Program schema: `label(arg_extreme(shot_options, metric=pop_count_after_shot(option), direction=highest)); scene=marble_chain; scope=max_pop_direction_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
