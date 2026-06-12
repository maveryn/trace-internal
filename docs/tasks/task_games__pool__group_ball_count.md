# `task_games__pool__group_ball_count`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/pool/`
3. Scene id: `pool`
4. Public task id: `task_games__pool__group_ball_count`
5. Supported `query_id` values: `current_group_ball_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(balls, ball_group=current_player_group)); scene=pool; scope=group_ball_count; query_branch=current_group_ball_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
