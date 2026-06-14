# `task_games__bingo__completed_line_sum_value`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Public task id: `task_games__bingo__completed_line_sum_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_set`
7. Program schema: `sum(values(cells(completed_line))); scene=bingo; scope=completed_line_sum_value`

## Program Contract
- `sum(values(cells(completed_line))); scene=bingo; scope=completed_line_sum_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
