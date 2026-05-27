# `task_games__minigolf__first_obstacle_label`

1. Domain: `games`
2. Task group: `minigolf`
3. Scene id: `minigolf`
4. Query id: `first_obstacle_label`
5. Prompt bundle: `games_minigolf_v0`

The image shows a mini-golf putting course with a ball, a hole, obstacles, and a short dashed cue. The cue gives the starting direction of the putt. The task asks for the label of the first obstacle reached when that cue is extended as a straight line.

The answer is a string obstacle label. Evidence is `bbox_set`: one pixel bounding box around the first obstacle hit by the extended cue.

Generation is deterministic for a fixed seed and records the hidden line trace, obstacle geometry, selected target obstacle, prompt keys, render style, and projected evidence in the trace payload.
