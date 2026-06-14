# `task_games__brick_breaker__hit_row_remaining_count`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/brick_breaker/`
3. Scene id: `brick_breaker`
4. Public task id: `task_games__brick_breaker__hit_row_remaining_count`
5. Supported `query_id` values: `hit_row_remaining_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(bricks_in_hit_row, state=remaining_after_marked_hit)); scene=brick_breaker; scope=hit_row_remaining_count`

## Program Contract
- `count(filter(bricks_in_hit_row, state=remaining_after_marked_hit)); scene=brick_breaker; scope=hit_row_remaining_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
