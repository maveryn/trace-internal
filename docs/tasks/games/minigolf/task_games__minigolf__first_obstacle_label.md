# `task_games__minigolf__first_obstacle_label`

## Contract
1. Domain: `games`
2. Scene id: `minigolf`
3. Public task id: `task_games__minigolf__first_obstacle_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `point`

## Program Contract
`label(first_collision(shot_path, obstacles)); scene=minigolf; scope=first_obstacle_label`

The rendered course shows one ball, a dashed cue direction, a hole, and labeled
obstacles. The program extends the shown cue as a straight line from the ball,
finds the first obstacle intersected by that ray, returns that obstacle label,
and annotates the obstacle center point.

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. Annotation is projected from the same generated game state used for answer verification.
