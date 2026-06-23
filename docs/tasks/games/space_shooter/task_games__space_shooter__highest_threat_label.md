# `task_games__space_shooter__highest_threat_label`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__highest_threat_label`
5. Supported `query_id` values: `single`
6. Answer schema: `string_label`
7. Annotation schema: `bbox`

## Program Contract
`label(arg_extreme(enemies, metric=bottom_proximity(enemy), direction=max)); scene=space_shooter; scope=highest_threat_label`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the scalar bbox of the one selected enemy ship.
3. Scalar annotation checked: true.
