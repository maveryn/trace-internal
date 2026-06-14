# `task_games__hex__connection_gap_count`

## Contract
1. Domain: `games`
2. Scene: `hex`
3. Scene id: `hex`
4. Public task id: `task_games__hex__connection_gap_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(unique_minimum_empty_cells_to_connect_sides(player, board_state)); scene=hex; scope=connection_gap_count`

## Program Contract
- `count(unique_minimum_empty_cells_to_connect_sides(player, board_state)); scene=hex; scope=connection_gap_count`

## Generation Notes
1. `query_id=single` is the public no-branch query id; the prompt uses the Hex connection-gap template.
2. The generator rejects boards with multiple distinct minimum gap sets so annotation has a unique witness set.
3. Annotation is the point set for the empty cells in that unique minimum connection gap.
