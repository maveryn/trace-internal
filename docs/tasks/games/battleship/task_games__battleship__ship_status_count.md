# `task_games__battleship__ship_status_count`

## Contract
1. Domain: `games`
2. Scene id: `battleship`
3. Public task id: `task_games__battleship__ship_status_count`
4. Supported `query_id` values: `sunk_ship_count`, `partial_ship_count`
5. Answer schema: `integer_count`
6. Annotation schema: `keyed_point_set_map`
7. Program schema: `count(filter(ships, ship_status=target_status)); scene=battleship; scope=ship_status_count; query_branch=partial_ship_count`

## Program Contract
- `count(filter(ships, ship_status=target_status)); scene=battleship; scope=ship_status_count; query_branch=partial_ship_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
