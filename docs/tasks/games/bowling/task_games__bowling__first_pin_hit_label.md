# `task_games__bowling__first_pin_hit_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/bowling/`
3. Scene id: `bowling`
4. Public task id: `task_games__bowling__first_pin_hit_label`
5. Supported `query_id` values: `single`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(first_collision(ball_path, pins)); scene=bowling; scope=first_pin_hit_label`

## Program Contract
- `label(first_collision(ball_path, pins)); scene=bowling; scope=first_pin_hit_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
