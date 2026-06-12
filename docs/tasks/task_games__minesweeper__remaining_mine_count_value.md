# `task_games__minesweeper__remaining_mine_count_value`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__remaining_mine_count_value`
4. Supported `query_id` values: `remaining_mine_count`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_set`
7. Program schema: `clue_value(marked_clue)-adjacent_flag_count(marked_clue); scene=minesweeper; scope=marked_clue_remaining_mine_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is the marked opened clue cell bbox, projected from the same generated game state used for answer verification.
