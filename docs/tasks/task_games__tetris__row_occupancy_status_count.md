# `task_games__tetris__row_occupancy_status_count`

## Contract
1. Domain: `games`
2. Task group: `tetris`
3. Scene id: `tetris`
4. Public task id: `task_games__tetris__row_occupancy_status_count`
5. Supported `query_id` values: `full_row_count`, `one_gap_row_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(board_rows, occupancy_status(row) = requested_status)); scene=tetris; scope=row_occupancy_status_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks whole qualifying row bounding boxes on the rendered board.
