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
`sum_by_lane(min(count(blue_player_shots), count(enemy_ships))); scene=space_shooter; scope=enemy_ship_hit_count`

## Generation Notes
1. `single` is the only public query id; the task-specific prompt key is trace metadata.
2. Blue player shots move upward in their lane; each visible blue shot can destroy one enemy ship above it in that same lane.
3. A lane can contain zero to three blue player shots and zero to three enemy ships.
4. If a lane has fewer blue shots than enemy ships, the lower enemy ships are destroyed first; this makes the annotated ship set unique.
5. The sampler annotates the destroyed enemy ship bounding boxes.
6. Red enemy shots and lanes without usable blue shots are visual distractors.
7. Scalar annotation checked: true.
