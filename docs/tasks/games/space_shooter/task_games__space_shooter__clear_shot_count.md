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
`count(filter(enemy_targets, lower_enemy_or_player_shot_below(target)=False)); scene=space_shooter; scope=clear_shot_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the bbox set of enemy ships counted as clear shots; red enemy shots are distractors, while blue player shots below an enemy block that enemy's clear shot.
3. Scalar annotation checked: true.
