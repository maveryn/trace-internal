# `task_games__brick_breaker__paddle_catch_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/brick_breaker/`
3. Scene id: `brick_breaker`
4. Public task id: `task_games__brick_breaker__paddle_catch_label`
5. Supported `query_id` values: `paddle_catch_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(paddle_zone_intersected_by(ball_trajectory)); scene=brick_breaker; scope=paddle_catch_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
