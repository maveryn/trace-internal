# `task_games__space_shooter__first_player_shot_hit_label`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__first_player_shot_hit_label`
5. Supported `query_id` values: `single`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox`

## Program Contract
`select(label in visible_candidate_player_shots where distance_to_first_same_lane_enemy_above is minimal); scene=space_shooter; scope=first_player_shot_hit_label`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Exactly four blue player shots are visibly labeled `A` through `D`.
3. Blue player shots move upward in their lane; each labeled shot first hits the nearest enemy ship above it in that same lane.
4. The four labeled shots have unique first-hit distances, so exactly one reaches an enemy first.
5. Annotation is the scalar bbox of the selected blue projectile itself; the nearby letter badge is not the annotated object.
6. Enemy ships and red enemy shots are visual distractors; only the labeled blue shots are answer options.
7. Scalar annotation checked: true.
