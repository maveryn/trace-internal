# `task_games__platformer__collectible_count`

## Contract
1. Domain: `games`
2. Task group: `platformer`
3. Scene id: `platformer`
4. Public task id: `task_games__platformer__collectible_count`
5. Supported `query_id` values: `collectible_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(collectibles, collected_by_route=True)); scene=platformer; scope=collectible_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
