# `task_games__pool__blocking_ball_count`

## Program Contract

- Program schema: `count(filter(pool_balls, intersects_marked_shot_segment)); scene=pool; scope=blocking_ball_count`
- Domain: `games`
- Scene id: `pool`
- Public task id: `task_games__pool__blocking_ball_count`
- Supported `query_id` values: `single`
- Answer schema: `integer`
- Annotation schema: `point_set`
- Output binding: answer is the number of other balls blocking either straight segment of the shown shot; annotation is one point at each blocking ball center.

## Generation Notes

- The shown shot has two straight segments: cue ball to the marked target ball, then the marked target ball to the marked pocket.
- Annotation is projected from the same generated pool state used for answer verification.
