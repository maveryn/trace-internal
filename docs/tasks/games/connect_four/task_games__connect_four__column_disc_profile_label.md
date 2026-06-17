# `task_games__connect_four__column_disc_profile_label`

## Contract
1. Domain: `games`
2. Scene id: `connect_four`
3. Public task id: `task_games__connect_four__column_disc_profile_label`
4. Supported `query_id` values: `single`
5. Answer schema: `label_string`
6. Annotation schema: `bbox_set`
7. Program schema: `select(column_label, red_disc_count_in_column=target_red_count and yellow_disc_count_in_column=target_yellow_count); scene=connect_four; scope=column_disc_profile_label`

## Program Contract
- `select(column_label, red_disc_count_in_column=target_red_count and yellow_disc_count_in_column=target_yellow_count); scene=connect_four; scope=column_disc_profile_label`

## Generation Notes
1. Column labels are rendered below the board, and a unique column matches the requested red/yellow count profile.
2. Annotation contains bboxes for every occupied disc cell in the selected column, not the column label text.
3. The requested red and yellow counts are sampled as task operands and recorded in trace metadata.
