# `task_games__match3__max_clear_swap_label`

## Contract
1. Domain: `games`
2. Scene id: `match3`
3. Public task id: `task_games__match3__max_clear_swap_label`
4. Supported `query_id` values: `max_clear_swap_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_set`
7. Program schema: `label(arg_extreme(swap_options, metric=cleared_count_after_swap(option), direction=highest)); scene=match3; scope=max_clear_swap_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
