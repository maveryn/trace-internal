# `task_games__bubble_shooter__drop_count`

## Contract
1. Domain: `games`
2. Task group: `bubble_shooter`
3. Scene id: `bubble_shooter`
4. Public task id: `task_games__bubble_shooter__drop_count`
5. Supported `query_id` values: `drop_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(disconnected_bubbles_after_pop(marked_shot)); scene=bubble_shooter; scope=drop_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
