# `task_games__battleship__ship_status_count`

## Contract
1. Domain: `games`
2. Task group: `battleship`
3. Scene id: `battleship`
4. Public task id: `task_games__battleship__ship_status_count`
5. Supported `query_id` values: `partial_ship_count`, `sunk_ship_count`
6. Answer schema: `integer_count`
7. Annotation schema: `keyed_point_set_map`
8. Program schema: `count(filter(ships, ship_status=target_status)); scene=battleship; scope=ship_status_count; query_branch=partial_ship_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
