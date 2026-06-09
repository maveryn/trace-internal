# `task_games__connect_four__winning_move_column_label`

## Contract
1. Domain: `games`
2. Task group: `connect_four`
3. Scene id: `connect_four`
4. Public task id: `task_games__connect_four__winning_move_column_label`
5. Supported `query_id` values: `winning_move_column_label`
6. Answer schema: `label_string`
7. Annotation schema: `bbox_set`
8. Program schema: `select(column_label, legal_drop_result=immediate_win_for_current_player); scene=connect_four; scope=winning_move_column_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Column labels are rendered below the board; annotation marks the selected column's landing cell, not the label text.
3. Annotation is projected from the same generated game state used for answer verification.
