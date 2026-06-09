# `task_games__cards__longest_run_length`

## Contract
1. Domain: `games`
2. Task group: `cards`
3. Scene id: `cards`
4. Public task id: `task_games__cards__longest_run_length`
5. Supported `query_id` values: `longest_run_length`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `max(lengths(consecutive_rank_runs(cards_in_display_order))); scene=cards; scope=longest_run_length`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
