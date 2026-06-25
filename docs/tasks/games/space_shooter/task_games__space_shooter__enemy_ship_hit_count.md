# `task_games__space_shooter__enemy_ship_hit_count`

## Contract
1. Domain: `games`
2. Scene: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__enemy_ship_hit_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
`count(enemy_ships_destroyable_by_current_blue_shots); scene=space_shooter; scope=enemy_ship_hit_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Blue player shots move upward in their lane; each visible blue shot can destroy one enemy ship above it in that same lane.
3. The sampler makes the destroyed enemy ships unique by construction and annotates those enemy ship bounding boxes.
4. Red enemy shots and lanes without usable blue shots are visual distractors.
5. Scalar annotation checked: true.
