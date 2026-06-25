# `task_games__space_shooter__first_hit_enemy_ship_label`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__first_hit_enemy_ship_label`
5. Supported `query_id` values: `single`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox`

## Program Contract
`select(label in visible_candidate_enemy_ships where distance_from_current_same_lane_player_shot_below is minimal); scene=space_shooter; scope=first_hit_enemy_ship_label`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Exactly four enemy ships are visibly labeled `A` through `D`.
3. Blue player shots move upward in their lane and hit the lower same-lane enemy ship first.
4. The four labeled ships have unique hit distances from the current blue shots, so exactly one labeled ship is hit first.
5. Annotation is the scalar bbox of the selected labeled enemy ship.
6. Unlabeled enemy ships and red enemy shots are visual distractors; only the labeled enemy ships are answer options.
7. Scalar annotation checked: true.
