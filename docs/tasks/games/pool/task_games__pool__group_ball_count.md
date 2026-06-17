# `task_games__pool__group_ball_count`

## Program Contract

- Program schema: `count(filter(pool_balls, group=current_player_group)); scene=pool; scope=group_ball_count`
- Domain: `games`
- Scene id: `pool`
- Public task id: `task_games__pool__group_ball_count`
- Supported `query_id` values: `single`
- Answer schema: `integer`
- Annotation schema: `bbox_set`
- Output binding: answer is the number of visible non-cue balls whose standard pool group is the current player's group; annotation is one bbox around each matching ball.

## Generation Notes

- The current player group is either `solids` or `stripes`; the sampled group is trace metadata, not a public query branch.
- Annotation is projected from the same generated pool state used for answer verification.
