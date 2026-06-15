# `task_games__dominoes__invalid_join_label`

## Contract
1. Domain: `games`
2. Scene: `dominoes`
3. Scene id: `dominoes`
4. Public task id: `task_games__dominoes__invalid_join_label`
5. Supported `query_id` values: `single`
6. Answer schema: `option_label`
7. Annotation schema: `segment`
8. Program schema: `label(select(join, touching_pip_left(join) != touching_pip_right(join))); scene=dominoes; scope=invalid_join_label`

## Program Contract
- `label(select(join, touching_pip_left(join) != touching_pip_right(join))); scene=dominoes; scope=invalid_join_label`

## Generation Notes
1. Renders one face-up domino chain with seven dominoes and exactly six labeled joins `A` through `F`.
2. Exactly one adjacent join has mismatched touching halves.
3. The answer is the label of that invalid join.
4. Annotation is one `segment` `[[x1, y1], [x2, y2]]` connecting the centers of the two touching domino halves at the invalid join.
