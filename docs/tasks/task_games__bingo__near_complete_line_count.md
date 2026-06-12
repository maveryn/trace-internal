# `task_games__bingo__near_complete_line_count`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Public task id: `task_games__bingo__near_complete_line_count`
4. Supported `query_id` values: `near_complete_column_count`, `near_complete_row_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(bingo_lines, unmarked_cell_count(line) = 1)); scene=bingo; scope=near_complete_line_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the single unmarked gap cell for each qualifying near-complete row or column.
