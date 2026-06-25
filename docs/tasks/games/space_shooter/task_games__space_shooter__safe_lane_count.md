# `task_games__space_shooter__safe_lane_count`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__safe_lane_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(filter(bottom_lane_pads, enemy_projectile_count(lane)=0)); scene=space_shooter; scope=safe_lane_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Annotation is the bbox set of safe bottom lane pads; only red enemy shots make a lane unsafe.
3. An unsafe lane may contain one to three visible red enemy shots.
4. Blue player shots are placed below all same-lane enemy ships and red enemy shots.
5. Scalar annotation checked: true.
