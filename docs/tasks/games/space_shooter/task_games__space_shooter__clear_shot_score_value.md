# `task_games__space_shooter__clear_shot_score_value`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__clear_shot_score_value`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`

## Program Contract
`sum(score(enemy) for enemy in enemy_targets if lower_enemy_or_player_shot_below(enemy)=False); scene=space_shooter; scope=clear_shot_score_value`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the bbox set of enemy ships whose printed score contributes to the answer; red enemy shots are distractors, while blue player shots below an enemy block that enemy's clear shot.
3. Scalar annotation checked: true.
