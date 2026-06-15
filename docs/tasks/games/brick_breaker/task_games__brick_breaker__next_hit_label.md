# `task_games__brick_breaker__next_hit_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/brick_breaker/`
3. Scene id: `brick_breaker`
4. Public task id: `task_games__brick_breaker__next_hit_label`
5. Supported `query_id` values: `single`
6. Answer schema: `string_label`
7. Annotation schema: `point`
8. Program schema: `label(first_collision(ball_trajectory, bricks)); scene=brick_breaker; scope=next_hit_label`

## Program Contract
- `label(first_collision(ball_trajectory, bricks)); scene=brick_breaker; scope=next_hit_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is one point at the center of the selected first-hit brick, projected from the same generated game state used for answer verification.
