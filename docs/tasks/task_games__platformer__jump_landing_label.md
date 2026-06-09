# `task_games__platformer__jump_landing_label`

## Contract
1. Domain: `games`
2. Task group: `platformer`
3. Scene id: `platformer`
4. Public task id: `task_games__platformer__jump_landing_label`
5. Supported `query_id` values: `jump_landing_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(landing_platform(marked_jump)); scene=platformer; scope=jump_landing_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
