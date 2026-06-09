# `task_games__2048__merge_count`

## Contract
1. Domain: `games`
2. Task group: `2048`
3. Scene id: `2048`
4. Public task id: `task_games__2048__merge_count`
5. Supported `query_id` values: `merge_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events); scene=2048; scope=merge_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
