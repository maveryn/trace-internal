# `task_games__battleship__ship_cell_status_count`

## Contract
1. Domain: `games`
2. Scene id: `battleship`
3. Public task id: `task_games__battleship__ship_cell_status_count`
4. Supported `query_id` values: `named_ship_hit_cell_count`, `named_ship_unhit_cell_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(cells(target_ship), cell_status=target_status)); scene=battleship; scope=ship_cell_status_count`

## Program Contract
- `count(filter(cells(target_ship), cell_status=target_status)); scene=battleship; scope=ship_cell_status_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Target ships are sampled from the five active fleet shapes: `Line 5`, `Line 4`, `Line 3`, `Square 2x2`, and `L 3`.
4. Annotation is projected from the counted target-ship cell boxes used for answer verification.
