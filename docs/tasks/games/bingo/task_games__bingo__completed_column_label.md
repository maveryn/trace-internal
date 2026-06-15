# `task_games__bingo__completed_column_label`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Public task id: `task_games__bingo__completed_column_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `segment`
7. Program schema: `label(unique_completed_column(board)); scene=bingo; scope=completed_column_label`

## Program Contract
- `label(unique_completed_column(board)); scene=bingo; scope=completed_column_label`

## Generation Notes
1. The card has exactly one completed BINGO column.
2. The answer is one of `B`, `I`, `N`, `G`, or `O`.
3. Annotation is the top-to-bottom cell-center segment for the completed column.
