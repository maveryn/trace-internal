# `task_pages__data_table__row_filter_count`

## Contract
1. Domain: `pages`
2. Scene id: `data_table`
3. Task group: `counting`
4. Task id: `task_pages__data_table__row_filter_count`
5. Objective: count sectioned GUI table rows matching a visible row predicate.

## Query IDs
1. `selected_rows_with_status_count`
2. `enabled_action_for_type_count`
3. `value_threshold_in_group_count`

## Answer And Evidence
Answers are integers. Evidence is a `bbox_set` over full row bboxes for every counted row. Table cell and candidate-label badge bboxes stay trace metadata only.
