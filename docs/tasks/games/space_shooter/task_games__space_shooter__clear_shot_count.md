# `task_games__space_shooter__clear_shot_count`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__clear_shot_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(filter(enemy_targets, shot_line_blocked(target)=False)); scene=space_shooter; scope=clear_shot_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the bbox set of enemy ships counted as clear shots.
3. Scalar annotation checked: true.
