# `task_pages__control_board__control_filter_count`

## Contract
1. Domain: `pages`
2. Scene id: `control_board`
3. Task group: `counting`
4. Task id: `task_pages__control_board__control_filter_count`
5. Objective: count grouped GUI controls matching a visible state predicate.

## Query IDs
1. `disabled_controls_in_group_count`
2. `selected_enabled_controls_in_group_count`

## Answer And Evidence
Answers are integers. Evidence is a `bbox_set` over full control bboxes for every counted control. Candidate-label badge bboxes stay trace metadata only.
