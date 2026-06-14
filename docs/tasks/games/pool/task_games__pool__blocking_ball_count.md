# `task_games__pool__blocking_ball_count`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/pool/`
3. Scene id: `pool`
4. Public task id: `task_games__pool__blocking_ball_count`
5. Supported `query_id` values: `blocking_ball_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(balls, blocks_shot_line(ball, cue_ball, target_pocket)=True)); scene=pool; scope=blocking_ball_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
