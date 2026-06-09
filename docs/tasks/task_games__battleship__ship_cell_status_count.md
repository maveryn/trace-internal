# `task_games__battleship__ship_cell_status_count`

## Contract
1. Domain: `games`
2. Task group: `battleship`
3. Scene id: `battleship`
4. Public task id: `task_games__battleship__ship_cell_status_count`
5. Supported `query_id` values: `named_ship_hit_cell_count`, `named_ship_unhit_cell_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(cells(target_ship), cell_status=target_status)); scene=battleship; scope=ship_cell_status_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Target ships are sampled from the five active fleet shapes: `Line 5`, `Line 4`, `Line 3`, `Square 2x2`, and `L 3`.
4. Annotation is projected from the counted target-ship cell centers used for answer verification.
