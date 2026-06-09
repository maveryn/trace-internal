# `task_games__bingo__completed_line_count`

## Contract
1. Domain: `games`
2. Task group: `bingo`
3. Scene id: `bingo`
4. Public task id: `task_games__bingo__completed_line_count`
5. Supported `query_id` values: `completed_axis_line_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(completed_lines(board, axis_scope)); scene=bingo; scope=completed_line_count; query_branch=completed_axis_line_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
