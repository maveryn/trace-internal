# `task_games__connect_four__winning_move_column_label`

## Contract
1. Domain: `games`
2. Scene id: `connect_four`
3. Public task id: `task_games__connect_four__winning_move_column_label`
4. Supported `query_id` values: `single`
5. Answer schema: `label_string`
6. Annotation schema: `point_set`
7. Program schema: `select(column_label, legal_drop_result=immediate_win_for_current_player); scene=connect_four; scope=winning_move_column_label`

## Program Contract
- `select(column_label, legal_drop_result=immediate_win_for_current_player); scene=connect_four; scope=winning_move_column_label`

## Generation Notes
1. Column labels are rendered below the board; annotation marks the center of the selected column's landing cell, not the label text.
2. The answer landing cell is not visibly highlighted in the rendered image.
3. Annotation is projected from the same generated game state used for answer verification.
