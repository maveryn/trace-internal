# `task_games__marble_chain__target_pop_direction_label`

## Contract
1. Domain: `games`
2. Task group: `marble_chain`
3. Scene id: `marble_chain`
4. Public task id: `task_games__marble_chain__target_pop_direction_label`
5. Supported `query_id` values: `target_pop_direction_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(select_option(shot_options, option_value=target_pop_count, option_metric=pop_count_after_shot(option))); scene=marble_chain; scope=target_pop_direction_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
